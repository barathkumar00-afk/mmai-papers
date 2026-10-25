"""Short-lived, in-memory case store.

A completed multimodal analysis is cached so that ``/api/generate/explanation``
and ``/api/generate/report`` can reference it by ``case_id`` without re-running
inference.

Privacy: nothing is persisted to disk. Entries expire after ``CASE_TTL_SECONDS``
and are bounded by ``CASE_MAX_ENTRIES``. Because this is a clinical research
prototype, only the minimum required to serve the follow-up endpoints is kept.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

CASE_TTL_SECONDS = 1800
CASE_MAX_ENTRIES = 32


class CaseStore:
    """Bounded TTL cache of :class:`MultimodalAnalysisResponse` objects."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entries: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

    def _prune(self) -> None:
        now = time.monotonic()
        stale = [key for key, entry in self._entries.items() if entry["expires_at"] <= now]
        for key in stale:
            self._entries.pop(key, None)
        while len(self._entries) > CASE_MAX_ENTRIES:
            self._entries.popitem(last=False)

    def put(self, case_id: str, analysis: Any) -> None:
        if not case_id:
            return
        with self._lock:
            self._prune()
            self._entries[case_id] = {
                "analysis": analysis,
                "stored_at": time.time(),
                "expires_at": time.monotonic() + CASE_TTL_SECONDS,
            }
            self._entries.move_to_end(case_id)

    def get(self, case_id: str) -> Optional[Any]:
        if not case_id:
            return None
        with self._lock:
            self._prune()
            entry = self._entries.get(case_id)
            return entry["analysis"] if entry else None

    def ids(self) -> List[str]:
        with self._lock:
            self._prune()
            return list(self._entries.keys())

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


case_store = CaseStore()
