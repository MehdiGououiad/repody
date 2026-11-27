"""Domain errors mapped to HTTP status codes in the API layer."""


class CoreError(Exception):
    """Base error with HTTP status code and safe user-facing detail."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class NotFoundError(CoreError):
    """Requested resource does not exist or is outside the caller's account."""

    def __init__(self, detail: str = "Resource not found.") -> None:
        super().__init__(404, detail)


class ConflictError(CoreError):
    """Operation is not valid for the resource's current lifecycle state."""

    def __init__(self, detail: str) -> None:
        super().__init__(409, detail)


class FourEyesViolationError(CoreError):
    """Raised when Maker and Checker are the same actor."""

    def __init__(
        self,
        detail: str = "Four-eyes violation: the Checker must be a different user than the Maker.",
    ) -> None:
        super().__init__(403, detail)
