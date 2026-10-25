"""Ingest the local knowledge directory into the FAISS index.

Usage
-----
    cd backend
    python -m scripts.ingest_knowledge            # add/refresh all documents
    python -m scripts.ingest_knowledge --rebuild  # discard and rebuild from scratch
    python -m scripts.ingest_knowledge --query "ground glass opacity"   # smoke test

Notes
-----
* Only files inside ``backend/data/knowledge`` are read. There is no network
  fetch and no external document source: every citation the API can return must
  be traceable to a file on this disk.
* Documents are plain Markdown. An optional ``---`` front-matter block at the
  top supplies ``title``, ``societies`` and ``source``.
* No PMID or DOI is inferred or invented. Metadata records the real filename.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import ensure_directories, get_settings  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.services.retrieval_service import retrieval_service  # noqa: E402

logger = get_logger("scripts.ingest_knowledge")

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".rst", ".json", ".text"}

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_PROVENANCE = re.compile(r"^PROVENANCE:\s*(.+)$", re.MULTILINE)


def parse_frontmatter(raw: str) -> Dict[str, str]:
    """Return the leading ``---`` block as a flat string mapping."""
    match = _FRONTMATTER.match(raw)
    if not match:
        return {}
    fields: Dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip().lower()] = value.strip().strip("\"'")
    return fields


def derive_title(text: str, path: Path) -> str:
    fields = parse_frontmatter(text)
    if fields.get("title"):
        return fields["title"]
    for line in text.splitlines():
        candidate = line.strip().lstrip("#").strip()
        if candidate and not candidate.upper().startswith("PROVENANCE"):
            return candidate.rstrip(".")
        if candidate.upper().startswith("PROVENANCE"):
            break
    return path.stem.replace("_", " ").replace("-", " ").title()


def strip_preamble(text: str) -> str:
    """Drop the front-matter block; keep the PROVENANCE line (it is load-bearing)."""
    return _FRONTMATTER.sub("", text, count=1).strip()


def collect_documents(directory: Path) -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if path.name.startswith("."):
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("unreadable", extra={"file": path.name, "error": str(exc)})
            continue
        if path.suffix.lower() == ".json":
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning("bad_json", extra={"file": path.name, "error": str(exc)})
                continue
            if isinstance(payload, list):
                for index, item in enumerate(payload):
                    if not isinstance(item, dict):
                        continue
                    documents.append(_json_document(item, path, index))
            elif isinstance(payload, dict):
                documents.append(_json_document(payload, path, 0))
            continue
        documents.append(
            {
                "document_id": f"local-{path.stem}",
                "title": derive_title(raw, path),
                "text": strip_preamble(raw),
                "source_path": str(path),
                "source_file": path.name,
                "source": f"local_reference_note:{path.name}",
                "societies": [],
                "provenance": (
                    _PROVENANCE.search(raw).group(1).strip()
                    if _PROVENANCE.search(raw)
                    else "local_reference_note"
                ),
            }
        )
    return documents


def _json_document(item: Dict[str, Any], path: Path, index: int) -> Dict[str, Any]:
    return {
        "document_id": str(item.get("document_id") or f"local-{path.stem}-{index}"),
        "title": str(item.get("title") or path.stem),
        "text": str(item.get("text") or item.get("content") or ""),
        "source_path": str(path),
        "source_file": path.name,
        "source": str(item.get("source") or f"local_reference_note:{path.name}"),
        "societies": [str(s) for s in (item.get("societies") or [])],
        "provenance": str(item.get("provenance") or "local_reference_note"),
    }


async def run(rebuild: bool, query: str | None) -> int:
    settings = get_settings()
    ensure_directories()

    if rebuild:
        retrieval_service.reset()
        logger.info("index_reset")

    documents = collect_documents(settings.knowledge_dir)
    if not documents:
        logger.error("no_documents", extra={"directory": str(settings.knowledge_dir)})
        return 1

    total_chars = sum(len(d.get("text") or "") for d in documents)
    logger.info(
        "ingest_start",
        extra={
            "documents": len(documents),
            "characters": total_chars,
            "encoder": embedding_label(),
            "rebuild": rebuild,
        },
    )

    summary = await retrieval_service.ingest(documents, rebuild=False)
    retrieval_service.save()

    status = retrieval_service.status()
    logger.info(
        "ingest_done",
        extra={
            "ingested": summary.get("ingested"),
            "chunks": status["total_chunks"],
            "documents_in_index": status["total_documents"],
            "dimension": status["dimension"],
            "index_type": status["index_type"],
        },
    )
    print(json.dumps({"ingest": summary, "status": status}, indent=2, default=str))

    if query:
        result = await retrieval_service.search(query, top_k=5)
        print("\n--- retrieval smoke test ---")
        print(f"query: {query}")
        print(f"message: {result.get('message') or '-'}")
        for item in result.get("evidence", []):
            title = item.get("title") if isinstance(item, dict) else getattr(item, "title", "?")
            sim = item.get("similarity") if isinstance(item, dict) else getattr(item, "similarity", "?")
            source = (
                item.get("source") if isinstance(item, dict) else getattr(item, "source", "?")
            )
            print(f"  [{sim:.4f}] {title}  ({source})")
    return 0


def embedding_label() -> str:
    from app.services.embedding_service import embedding_service

    info = embedding_service.info()
    return f"{info.name}/{info.role} status={info.status}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="reset before ingesting")
    parser.add_argument("--query", help="run a retrieval smoke test after ingesting")
    args = parser.parse_args()
    configure_logging()
    return asyncio.run(run(args.rebuild, args.query))


if __name__ == "__main__":
    raise SystemExit(main())
