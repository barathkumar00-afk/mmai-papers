"""Security helpers: upload validation, size limits and safe temporary files.

Design constraints for a clinical research prototype:
* Never persist patient-supplied uploads longer than necessary.
* Never execute or interpret uploaded content.
* Validate by magic bytes, not only by the client-supplied filename.
* Enforce size limits while streaming, so a large body is rejected early.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, Optional, Tuple

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode

# Magic-byte signatures used for content sniffing.
_MAGIC_SIGNATURES: Tuple[Tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
    (b"RIFF", "image/webp"),
    (b"RIFF", "audio/wav"),
    (b"fLaC", "audio/flac"),
    (b"OggS", "audio/ogg"),
    (b"ID3", "audio/mpeg"),
    (b"\x1a\x45\xdf\xa3", "video/webm"),
)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: Optional[str], default: str = "upload") -> str:
    """Strip path traversal and unsafe characters from a client filename."""
    raw = Path(name or default).name  # removes any directory component
    cleaned = _SAFE_NAME_RE.sub("_", raw).strip("._")
    return (cleaned or default)[:120]


_MIME_TO_EXT: Dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tif",
    "image/webp": ".webp",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/mpeg": ".mp3",
    "video/webm": ".webm",
}


def guess_extension(filename: Optional[str], data: bytes = b"") -> str:
    """Return a lowercase extension, preferring the detected content type."""
    if data and is_dicom(data):
        return ".dcm"
    for signature, mime in _MAGIC_SIGNATURES:
        if data[: len(signature)] == signature:
            if mime == "image/webp" and data[8:12] == b"WEBP":
                return ".webp"
            if mime in _MIME_TO_EXT:
                return _MIME_TO_EXT[mime]
    suffix = Path(sanitize_filename(filename)).suffix.lower()
    return suffix


def sniff_content_type(data: bytes) -> Optional[str]:
    """Best-effort content type detection from leading bytes."""
    for signature, mime in _MAGIC_SIGNATURES:
        if data[: len(signature)] == signature:
            return mime
    return None


def is_dicom(data: bytes) -> bool:
    """DICOM Part-10 files start with the ``DICM`` magic at offset 128."""
    return len(data) >= 132 and data[128:132] == b"DICM"


def is_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"


def validate_upload(
    *,
    filename: Optional[str],
    data: bytes,
    allowed_extensions: Iterable[str],
    content_prefix: str,
) -> Dict[str, object]:
    """Validate an in-memory upload and return its safe metadata.

    Raises:
        AppError: with a specific :class:`ErrorCode` on any validation failure.
    """
    settings = get_settings()
    allowed = {ext.lower() for ext in allowed_extensions}

    if not data:
        raise AppError(ErrorCode.INVALID_FILE, "The uploaded file is empty.", status_code=400)

    if len(data) > settings.max_upload_bytes:
        raise AppError(
            ErrorCode.FILE_TOO_LARGE,
            f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit.",
            status_code=413,
            details={"max_bytes": settings.max_upload_bytes, "received_bytes": len(data)},
        )

    safe_name = sanitize_filename(filename)
    extension = guess_extension(safe_name, data)
    if extension not in allowed:
        raise AppError(
            ErrorCode.UNSUPPORTED_FORMAT,
            f"Unsupported {content_prefix} format '{extension or 'unknown'}'.",
            status_code=415,
            details={"allowed": sorted(allowed)},
        )

    content_type = sniff_content_type(data) or "application/octet-stream"
    return {
        "filename": safe_name,
        "extension": extension,
        "content_type": content_type,
        "size_bytes": len(data),
        "is_dicom": is_dicom(data),
        "is_pdf": is_pdf(data),
    }


async def read_upload_limited(stream: BinaryIO, max_bytes: int, chunk_size: int = 1024 * 512) -> bytes:
    """Read at most ``max_bytes`` from a synchronous file-like upload stream.

    Raises ``AppError(FILE_TOO_LARGE)`` as soon as the limit is exceeded, without
    buffering the whole payload.
    """
    buffer = bytearray()
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise AppError(
                ErrorCode.UPLOAD_LIMIT_EXCEEDED,
                "Upload limit exceeded.",
                status_code=413,
                details={"max_bytes": max_bytes},
            )
    return bytes(buffer)


@contextlib.contextmanager
def secure_temp_file(suffix: str = "", max_age_seconds: Optional[int] = None):
    """Create a private temp file that is always removed on exit.

    The file is created with a random name inside the OS temp directory and is
    deleted whether or not the body raises.
    """
    tmp_dir = Path(tempfile.gettempdir()) / "medexplain-uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    handle, path_str = tempfile.mkstemp(prefix=f"{uuid.uuid4().hex}-", suffix=suffix, dir=str(tmp_dir))
    os.close(handle)
    path = Path(path_str)
    try:
        yield path
    finally:
        with contextlib.suppress(OSError):
            path.unlink()
        if max_age_seconds is not None:
            _prune_temp_dir(tmp_dir, max_age_seconds)


def _prune_temp_dir(directory: Path, max_age_seconds: int) -> None:
    """Best-effort removal of stale temp files (no patient data retention)."""
    import time

    now = time.time()
    with contextlib.suppress(OSError):
        for entry in directory.iterdir():
            if entry.is_file() and now - entry.stat().st_mtime > max_age_seconds:
                with contextlib.suppress(OSError):
                    entry.unlink()


def clear_temp_dir() -> None:
    """Remove every temp file produced by this service."""
    tmp_dir = Path(tempfile.gettempdir()) / "medexplain-uploads"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
