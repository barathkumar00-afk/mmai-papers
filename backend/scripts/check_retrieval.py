"""Ad-hoc retrieval smoke check. Not part of the pytest suite."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.retrieval_service import retrieval_service  # noqa: E402

QUERIES = [
    "ground glass opacity chest radiograph",
    "how do I distinguish pneumonia from pulmonary oedema",
    "anthracosis hyperinflation upper lobe",
    "PaO2 FiO2 ratio severity threshold",
    "signal to noise ratio transcript reliability",
]


async def main() -> None:
    print("load from disk:", retrieval_service.load())
    print("status:", {k: retrieval_service.status()[k] for k in
                      ("initialized", "total_chunks", "dimension", "index_type",
                       "loaded_from_disk")})
    for query in QUERIES:
        result = await retrieval_service.search(query, top_k=3)
        print(f"\n--- {query}")
        print("    message:", result.get("message") or "-")
        for item in result.get("evidence", []):
            print(f"    {item.similarity:+.4f}  {item.title[:58]:<58}  {item.source}")


if __name__ == "__main__":
    asyncio.run(main())
