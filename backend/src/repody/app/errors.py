"""The one application exception; ``main`` answers it as an HTTP error.

Plain Python on purpose: the use cases stay free of FastAPI and Starlette (import contracts in
pyproject.toml), and the web layer maps this to a response.
"""


class AppError(Exception):
    def __init__(self, status_code: int, detail: str, *, retry_after: int | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.retry_after = retry_after
