class AppError(Exception):
    """Base exception for all application-level errors."""
    def __init__(self, message: str, status_code: int = 500, internal_detail: str = ""):
        self.message = message
        self.status_code = status_code
        self.internal_detail = internal_detail
        super().__init__(message)


class ValidationError(AppError):
    """Raised when user input or data is invalid."""
    def __init__(self, message: str, internal_detail: str = ""):
        super().__init__(message, status_code=400, internal_detail=internal_detail)


class NotFoundError(AppError):
    """Raised when a requested resource is not found."""
    def __init__(self, message: str, internal_detail: str = ""):
        super().__init__(message, status_code=404, internal_detail=internal_detail)


class ConflictError(AppError):
    """Raised when there is a conflict, such as duplicate data or invalid state."""
    def __init__(self, message: str, internal_detail: str = ""):
        super().__init__(message, status_code=409, internal_detail=internal_detail)


class ProcessingError(AppError):
    """Raised when PDF processing or generation fails."""
    def __init__(self, message: str, internal_detail: str = ""):
        super().__init__(message, status_code=500, internal_detail=internal_detail)


class StorageError(AppError):
    """Raised when file IO operations fail."""
    def __init__(self, message: str, internal_detail: str = ""):
        super().__init__(message, status_code=500, internal_detail=internal_detail)
