"""Ollama client and LLM service.

Responsibilities
----------------
* Probe whether a local Ollama server is reachable.
* Probe whether the *configured* model is actually pulled.
* Generate text / structured JSON, and embeddings, over HTTP.
* Never raise on connectivity problems: availability is data, not an exception,
  so a missing Ollama can never take the whole API down.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from typing import Any, Dict, List, Optional, Sequence

import httpx

from app.core.config import get_settings
from app.core.errors import (
    AppError,
    ErrorCode,
    InferenceTimeoutError,
    ModelUnavailableError,
    OllamaUnavailableError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)


def extract_json(text: str) -> Optional[Any]:
    """Pull the first JSON value out of an LLM response.

    Handles fenced code blocks and common local-model preambles. Returns
    ``None`` when nothing parseable is found -- callers must handle that rather
    than inventing content.
    """
    if not text:
        return None
    candidate = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK_RE.search(candidate)
    if match:
        raw = match.group(0)
        for attempt in (raw, raw.replace("\n", " ")):
            try:
                return json.loads(attempt)
            except json.JSONDecodeError:
                continue
    return None


class OllamaClient:
    """Thin async HTTP client for a local Ollama server."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_LLM_MODEL
        self.timeout = httpx.Timeout(
            settings.OLLAMA_TIMEOUT_SECONDS, connect=settings.OLLAMA_CONNECT_TIMEOUT_SECONDS
        )

    # ------------------------------------------------------------- utilities
    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        # Optional, only forwarded when explicitly configured. Never required.
        import os

        token = os.getenv("OLLAMA_API_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, headers=self._headers())

    # ----------------------------------------------------------- availability
    async def list_models(self) -> List[Dict[str, Any]]:
        """Return installed model entries; empty list when unreachable."""
        try:
            async with await self._client() as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("ollama_tags_unavailable", extra={"error": str(exc)[:300]})
            return []
        models = payload.get("models", []) if isinstance(payload, dict) else []
        return [m for m in models if isinstance(m, dict)]

    @staticmethod
    def _matches(model_name: str, installed: Sequence[str]) -> bool:
        """Ollama tags often drop the tag suffix (``qwen2.5:7b`` -> ``qwen2.5``)."""
        if not model_name:
            return False
        target = model_name.strip().lower()
        if target in {name.lower() for name in installed}:
            return True
        if ":" not in target:
            return any(name.lower().split(":")[0] == target for name in installed)
        base = target.split(":")[0]
        return any(name.lower() == target or name.lower().split(":")[0] == base for name in installed)

    async def has_model(self, model: str) -> bool:
        installed = [str(m.get("name", "")) for m in await self.list_models()]
        return self._matches(model, installed)

    async def check_availability(self) -> Dict[str, Any]:
        """Non-raising health probe. Safe to call from request handlers."""
        settings = get_settings()
        result: Dict[str, Any] = {
            "available": False,
            "model": settings.OLLAMA_LLM_MODEL or None,
            "base_url": settings.OLLAMA_BASE_URL,
            "model_exists": False,
            "error": None,
        }
        if settings.MOCK_MODE:
            result.update(
                {
                    "available": True,
                    "mock_mode": True,
                    "status": "simulated",
                    "note": "MOCK_MODE=true: responses are deterministic simulations, "
                    "no Ollama call is made.",
                }
            )
            return result

        try:
            async with await self._client() as client:
                response = await client.get("/api/tags", timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            result["error"] = f"Local Ollama service is unavailable: {exc}"
            logger.warning("ollama_unavailable", extra={"error": str(exc)[:300]})
            return result

        models = payload.get("models", []) if isinstance(payload, dict) else []
        installed = [str(m.get("name", "")) for m in models if isinstance(m, dict)]
        model_exists = self._matches(settings.OLLAMA_LLM_MODEL, installed)
        result.update(
            {
                "available": True,
                "model_exists": model_exists,
                "status": "ready" if model_exists else "model_missing",
                "installed_models": installed,
            }
        )
        if not model_exists:
            result["error"] = (
                f"Configured model '{settings.OLLAMA_LLM_MODEL}' is not installed. "
                f"Run: ollama pull {settings.OLLAMA_LLM_MODEL}"
            )
        return result

    async def require_available(self, model: Optional[str] = None) -> None:
        """Raise a typed error when Ollama or the model is missing."""
        settings = get_settings()
        if settings.MOCK_MODE:
            return
        target = model or settings.OLLAMA_LLM_MODEL
        if not target:
            raise ModelUnavailableError("No Ollama model is configured (OLLAMA_LLM_MODEL is empty).")
        installed = [str(m.get("name", "")) for m in await self.list_models()]
        if not installed:
            raise OllamaUnavailableError(
                f"Local Ollama service is unavailable at {settings.OLLAMA_BASE_URL}. "
                "Start it with: ollama serve"
            )
        if not self._matches(target, installed):
            raise ModelUnavailableError(
                f"Configured model '{target}' is not installed. Run: ollama pull {target}"
            )

    # -------------------------------------------------------------- inference
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.1,
        num_predict: int = 1024,
        format_json: bool = False,
        extra_stop: Optional[List[str]] = None,
    ) -> str:
        """Generate a completion. Raises typed errors on failure."""
        settings = get_settings()
        target = model or settings.OLLAMA_LLM_MODEL
        if settings.MOCK_MODE:
            raise OllamaUnavailableError(
                "MOCK_MODE is enabled; no real generation is performed.", status_code=409
            )
        await self.require_available(target)

        options: Dict[str, Any] = {
            "temperature": temperature,
            "num_predict": num_predict,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
        }
        if extra_stop:
            options["stop"] = extra_stop

        body: Dict[str, Any] = {
            "model": target,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if system_prompt:
            body["system"] = system_prompt
        if format_json:
            body["format"] = "json"

        started = time.perf_counter()
        try:
            async with await self._client() as client:
                response = await client.post("/api/generate", json=body)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise InferenceTimeoutError(
                f"Ollama did not respond within {settings.OLLAMA_TIMEOUT_SECONDS}s."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ModelUnavailableError(
                f"Ollama returned HTTP {exc.response.status_code} for model '{target}'."
            ) from exc
        except Exception as exc:
            raise OllamaUnavailableError(f"Local Ollama service is unavailable: {exc}") from exc

        text = str(payload.get("response", "") or "").strip()
        logger.info(
            "ollama_generate",
            extra={
                "model": target,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "prompt_chars": len(prompt),
                "response_chars": len(text),
            },
        )
        return text

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.1,
        num_predict: int = 1536,
    ) -> Optional[Any]:
        """Generate and parse structured JSON. Returns ``None`` if unparseable."""
        text = await self.generate(
            prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            num_predict=num_predict,
            format_json=True,
        )
        return extract_json(text)

    async def generate_with_image(
        self,
        prompt: str,
        image_b64: str,
        *,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.1,
        num_predict: int = 768,
    ) -> str:
        """Vision-language generation via the Ollama ``images`` field."""
        settings = get_settings()
        target = model or settings.OLLAMA_VISION_MODEL or settings.OLLAMA_LLM_MODEL

        logger.info(f"Vision request: model={target}, prompt_len={len(prompt)}")

        if settings.MOCK_MODE:
            raise OllamaUnavailableError(
                "MOCK_MODE is enabled; no real vision inference is performed.", status_code=409
            )
        if not settings.OLLAMA_VISION_MODEL:
            raise AppError(
                ErrorCode.VISION_MODEL_UNAVAILABLE,
                "No vision model configured. Set OLLAMA_VISION_MODEL (e.g. qwen2.5vl:7b).",
                status_code=503,
            )
        await self.require_available(target)

        body = {
            "model": target,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": num_predict},
        }
        if system_prompt:
            body["system"] = system_prompt

        try:
            async with await self._client() as client:
                logger.info(f"Calling Ollama /api/generate for model {target}...")
                response = await client.post("/api/generate", json=body)
                response.raise_for_status()
                payload = response.json()
                logger.info(f"Ollama vision response received: {len(payload.get('response', ''))} chars")
        except httpx.TimeoutException as exc:
            logger.error(f"Vision timeout: {exc}")
            raise InferenceTimeoutError(
                f"Vision model did not respond within {settings.OLLAMA_TIMEOUT_SECONDS}s."
            ) from exc
        except Exception as exc:
            logger.error(f"Vision Ollama error: {exc}", exc_info=True)
            raise OllamaUnavailableError(f"Local Ollama service is unavailable: {exc}") from exc
        return str(payload.get("response", "") or "").strip()

    # -------------------------------------------------------------- embedding
    async def embed(self, texts: Sequence[str], *, model: Optional[str] = None) -> List[List[float]]:
        """Embed texts via ``/api/embed`` with a ``/api/embeddings`` fallback."""
        settings = get_settings()
        target = model or settings.embedding_model
        if not target:
            raise ModelUnavailableError(
                "No embedding model configured. Set OLLAMA_EMBEDDING_MODEL "
                "(e.g. nomic-embed-text) or change EMBEDDING_PROVIDER."
            )
        await self.require_available(target)
        items = [t if t.strip() else " " for t in texts]
        try:
            async with await self._client() as client:
                response = await client.post("/api/embed", json={"model": target, "input": items})
                if response.status_code == 200:
                    payload = response.json()
                    embeddings = payload.get("embeddings")
                    if isinstance(embeddings, list) and embeddings:
                        return [[float(x) for x in vec] for vec in embeddings]

                # Older servers only expose the single-input endpoint.
                vectors: List[List[float]] = []
                for text in items:
                    single = await client.post(
                        "/api/embeddings", json={"model": target, "prompt": text}
                    )
                    single.raise_for_status()
                    vector = single.json().get("embedding", [])
                    vectors.append([float(x) for x in vector])
                if vectors:
                    return vectors
        except httpx.TimeoutException as exc:
            raise InferenceTimeoutError("Ollama embedding request timed out.") from exc
        except ModelUnavailableError:
            raise
        except Exception as exc:
            raise OllamaUnavailableError(f"Local Ollama service is unavailable: {exc}") from exc
        raise ModelUnavailableError("Ollama returned no embedding vectors.")


ollama_client = OllamaClient()


# --------------------------------------------------------------------- service
class LLMService:
    """Application-facing reasoning service built on :class:`OllamaClient`.

    Every method degrades to an explicit, labelled simulation when no local model
    is available, so the API never fabricates content silently.
    """

    #: Instruction block shared by all clinical prompts.
    SAFETY_INSTRUCTIONS = (
        "You are a clinical decision-support reasoning component inside a research prototype.\n"
        "HARD RULES:\n"
        "1. Use ONLY the patient evidence and retrieved evidence provided. Never invent evidence.\n"
        "2. Cite ONLY retrieved document ids that appear in the context. Never invent citations.\n"
        "3. Never state certainty that the evidence does not support. Use hedged language.\n"
        "4. Clearly separate OBSERVED facts from your INTERPRETATION.\n"
        "5. Explicitly call out evidence that CONTRADICTS a candidate interpretation.\n"
        "6. List what additional information is required.\n"
        "7. Produce decision-support content only. Never produce a definitive diagnosis "
        "or an autonomous treatment decision."
    )

    def __init__(self, client: Optional[OllamaClient] = None) -> None:
        self.client = client or ollama_client

    @property
    def mock_mode(self) -> bool:
        return get_settings().MOCK_MODE

    async def availability(self) -> Dict[str, Any]:
        return await self.client.check_availability()

    async def complete(self, prompt: str, *, system_prompt: str = "", **kwargs: Any) -> Dict[str, Any]:
        """Return ``{'text', 'available', 'simulated', 'model', 'error'}``."""
        if self.mock_mode:
            return {
                "text": "",
                "available": False,
                "simulated": True,
                "model": get_settings().OLLAMA_LLM_MODEL,
                "error": "MOCK_MODE is enabled; no local LLM was called.",
            }
        try:
            text = await self.client.generate(
                prompt, system_prompt=system_prompt or self.SAFETY_INSTRUCTIONS, **kwargs
            )
            return {
                "text": text,
                "available": True,
                "simulated": False,
                "model": kwargs.get("model") or get_settings().OLLAMA_LLM_MODEL,
                "error": None,
            }
        except AppError as exc:
            logger.warning("llm_completion_failed", extra={"code": exc.code, "detail": exc.message})
            return {
                "text": "",
                "available": False,
                "simulated": False,
                "model": get_settings().OLLAMA_LLM_MODEL,
                "error": exc.message,
            }

    async def complete_json(self, prompt: str, *, system_prompt: str = "", **kwargs: Any) -> Dict[str, Any]:
        """Return ``{'data', 'available', 'simulated', 'error'}``; data may be ``None``."""
        if self.mock_mode:
            return {
                "data": None,
                "available": False,
                "simulated": True,
                "model": get_settings().OLLAMA_LLM_MODEL,
                "error": "MOCK_MODE is enabled; no local LLM was called.",
            }
        try:
            data = await self.client.generate_json(
                prompt, system_prompt=system_prompt or self.SAFETY_INSTRUCTIONS, **kwargs
            )
            return {
                "data": data,
                "available": data is not None,
                "simulated": False,
                "model": kwargs.get("model") or get_settings().OLLAMA_LLM_MODEL,
                "error": None if data is not None else "Model response was not valid JSON.",
            }
        except AppError as exc:
            logger.warning("llm_json_failed", extra={"code": exc.code, "detail": exc.message})
            return {
                "data": None,
                "available": False,
                "simulated": False,
                "model": get_settings().OLLAMA_LLM_MODEL,
                "error": exc.message,
            }

    async def describe_image(
        self, image_b64: str, context: str, *, focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """Vision-language description. Returns observations + an explicit caveat."""
        settings = get_settings()
        if self.mock_mode:
            return {
                "available": False,
                "simulated": True,
                "observations": [],
                "raw_text": "",
                "error": "MOCK_MODE is enabled; no vision model was called.",
            }
        if not settings.OLLAMA_VISION_MODEL:
            return {
                "available": False,
                "simulated": False,
                "observations": [],
                "raw_text": "",
                "error": "No vision model configured. Set OLLAMA_VISION_MODEL.",
            }
        prompt_parts = [
            "You are assisting a clinical research prototype. Describe ONLY what is visibly "
            "present in this medical image.",
            "Rules: describe observable features; do not give a diagnosis; do not state "
            "findings you cannot see; if the image is not a recognised modality or is "
            "unreadable, say so explicitly.",
        ]
        if focus:
            prompt_parts.append(f"Pay particular attention to: {focus}.")
        prompt_parts.append(f"Measured image properties computed locally:\n{context}")

        try:
            text = await self.client.generate_with_image(
                "\n".join(prompt_parts),
                image_b64,
                system_prompt=self.SAFETY_INSTRUCTIONS,
            )
        except AppError as exc:
            return {
                "available": False,
                "simulated": False,
                "observations": [],
                "raw_text": "",
                "error": exc.message,
            }
        return {
            "available": True,
            "simulated": False,
            "observations": _split_bullet_lines(text),
            "raw_text": text,
            "error": None,
        }


def _split_bullet_lines(text: str) -> List[str]:
    """Split a model description into observation lines."""
    if not text:
        return []
    lines: List[str] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*\u2022 ").strip()
        if len(line) >= 3:
            lines.append(line[:600])
    return lines[:20]


def encode_image_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


llm_service = LLMService()


async def gather_limited(coros: Sequence[Any], limit: int = 3) -> List[Any]:
    """Run coroutines with bounded concurrency, preserving order."""
    semaphore = asyncio.Semaphore(limit)

    async def _run(coro: Any) -> Any:
        async with semaphore:
            return await coro

    return await asyncio.gather(*[_run(c) for c in coros], return_exceptions=True)
