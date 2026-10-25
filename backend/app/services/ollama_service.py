import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_LLM_MODEL

    async def check_availability(self) -> dict:
        """Checks if the Ollama server is running and the model is available."""
        if settings.MOCK_MODE:
            return {
                "available": True,
                "model": self.model,
                "status": "MOCK_MODE"
            }

        try:
            async with httpx.AsyncClient() as client:
                # Check server health
                health_resp = await client.get(f"{self.base_url}/api/tags")
                if health_resp.status_code != 200:
                    return {"available": False, "error": "Server unavailable"}

                # Check if model is pulled
                tags = health_resp.json().get("models", [])
                model_exists = any(m["name"] == self.model for m in tags)

                return {
                    "available": True,
                    "model": self.model,
                    "exists": model_exists
                }
        except Exception as e:
            logger.error(f"Ollama connection error: {e}")
            return {"available": False, "error": str(e)}

    async def generate(self, prompt: str, system_prompt: str = ""):
        """Generates text using the configured Ollama model."""
        if settings.MOCK_MODE:
            return f"[MOCK RESPONSE] Based on the prompt: {prompt[:50]}... The clinical evidence suggests a simulated finding."

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "system": system_prompt,
                        "stream": False
                    }
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise RuntimeError(f"Failed to generate response from Ollama: {e}")

ollama_client = OllamaClient()
