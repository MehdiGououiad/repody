"""Domain errors mapped cleanly to HTTP status codes in the API layer."""


class FraudError(Exception):
    """Base error with HTTP status code and safe user-facing detail."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class NotFoundError(FraudError):
    """Requested analysis or artifact does not exist or is outside caller scope."""

    def __init__(self, detail: str = "Resource not found.") -> None:
        super().__init__(404, detail)


class ValidationError(FraudError):
    """Input document or payload failed integrity or validation checks."""

    def __init__(self, detail: str) -> None:
        super().__init__(422, detail)
