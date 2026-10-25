"""Predictable API error codes and the application exception type.

Every failure surfaces to the client as::

    {
      "success": false,
      "error": {
        "code": "OLLAMA_UNAVAILABLE",
        "message": "Local Ollama service is unavailable."
      }
    }

Stack traces are logged server-side only and never returned in production mode.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class ErrorCode:
    """Stable, machine-readable error codes."""

    INVALID_FILE = "INVALID_FILE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    MALFORMED_CLINICAL_DATA = "MALFORMED_CLINICAL_DATA"
    VALIDATION_ERROR = "VALIDATION_ERROR"

    OLLAMA_UNAVAILABLE = "OLLAMA_UNAVAILABLE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    INFERENCE_TIMEOUT = "INFERENCE_TIMEOUT"

    FAISS_INDEX_MISSING = "FAISS_INDEX_MISSING"
    EMBEDDING_MODEL_UNAVAILABLE = "EMBEDDING_MODEL_UNAVAILABLE"
    KNOWLEDGE_BASE_NOT_INITIALIZED = "KNOWLEDGE_BASE_NOT_INITIALIZED"

    SPEECH_MODEL_UNAVAILABLE = "SPEECH_MODEL_UNAVAILABLE"
    VISION_MODEL_UNAVAILABLE = "VISION_MODEL_UNAVAILABLE"

    UPLOAD_LIMIT_EXCEEDED = "UPLOAD_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


#: Human-readable default messages, safe to expose to clients.
DEFAULT_MESSAGES: Dict[str, str] = {
    ErrorCode.INVALID_FILE: "The uploaded file could not be read.",
    ErrorCode.FILE_TOO_LARGE: "The uploaded file exceeds the configured size limit.",
    ErrorCode.UNSUPPORTED_FORMAT: "The uploaded file format is not supported.",
    ErrorCode.MISSING_PARAMETER: "A required parameter is missing.",
    ErrorCode.MALFORMED_CLINICAL_DATA: "Clinical data could not be normalized.",
    ErrorCode.VALIDATION_ERROR: "Request validation failed.",
    ErrorCode.OLLAMA_UNAVAILABLE: "Local Ollama service is unavailable.",
    ErrorCode.MODEL_UNAVAILABLE: "The configured model is not available.",
    ErrorCode.INFERENCE_TIMEOUT: "Model inference exceeded the configured timeout.",
    ErrorCode.FAISS_INDEX_MISSING: "The FAISS retrieval index is not initialized.",
    ErrorCode.EMBEDDING_MODEL_UNAVAILABLE: "The embedding model is not available.",
    ErrorCode.KNOWLEDGE_BASE_NOT_INITIALIZED: "Knowledge base not initialized",
    ErrorCode.SPEECH_MODEL_UNAVAILABLE: "No local speech recognition model is available.",
    ErrorCode.VISION_MODEL_UNAVAILABLE: "No local vision-language model is available.",
    ErrorCode.UPLOAD_LIMIT_EXCEEDED: "Upload limit exceeded.",
    ErrorCode.INTERNAL_ERROR: "An internal error occurred.",
}


class AppError(Exception):
    """Domain error carrying a stable code, an HTTP status and safe details."""

    def __init__(
        self,
        code: str,
        message: Optional[str] = None,
        *,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.code = code
        self.message = message or DEFAULT_MESSAGES.get(code, "Request failed.")
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_payload(self) -> Dict[str, Any]:
        error: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            error["details"] = self.details
        return {"success": False, "error": error}


class OllamaUnavailableError(AppError):
    def __init__(self, message: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(ErrorCode.OLLAMA_UNAVAILABLE, message, status_code=503, **kwargs)


class ModelUnavailableError(AppError):
    def __init__(self, message: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(ErrorCode.MODEL_UNAVAILABLE, message, status_code=503, **kwargs)


class InferenceTimeoutError(AppError):
    def __init__(self, message: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(ErrorCode.INFERENCE_TIMEOUT, message, status_code=504, **kwargs)


class RetrievalUnavailableError(AppError):
    def __init__(self, code: str = ErrorCode.FAISS_INDEX_MISSING, message: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(code, message, status_code=503, **kwargs)


class ValidationFailure(AppError):
    def __init__(self, message: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(ErrorCode.VALIDATION_ERROR, message, status_code=422, **kwargs)
