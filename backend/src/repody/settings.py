"""Every AUDIT_* environment variable, in one pydantic-settings model.

Secrets are ``SecretStr``: they never appear in a repr, a log line or an error report (Sentry
serialises local variables); code reads them with ``get_secret_value()`` where it connects.
"""

from functools import lru_cache
from typing import Annotated, Self

from pydantic import (
    BeforeValidator,
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    SecretStr,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# A comma-separated env value (pydantic-settings' NoDecode recipe).
CommaList = Annotated[
    list[str],
    NoDecode,
    BeforeValidator(
        lambda v: [x.strip() for x in v.split(",") if x.strip()] if isinstance(v, str) else v
    ),
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUDIT_", env_file=".env", extra="ignore")

    # Platform
    deployment_environment: str = "development"
    debug: bool = False
    log_json: bool = True
    # Origins of browser apps that call the API directly (the web app goes through its own
    # server, same origin). Requests carry a bearer token, never cookies.
    cors_origins: CommaList = []
    seed_on_startup: bool = False

    # Postgres and S3 (Compose: SeaweedFS). The run queue is Hatchet: its client reads the
    # HATCHET_CLIENT_* environment (repody.infra.queue).
    database_url: SecretStr = SecretStr("postgresql+asyncpg://audit:audit@localhost:5432/repody")
    db_pool_size: PositiveInt = 10
    s3_endpoint_url: str = "http://localhost:8333"
    s3_region: str = "us-east-1"
    s3_access_key: str = "repody"
    s3_secret_key: SecretStr = SecretStr("s3-local-dev")
    s3_bucket: str = "audit-documents"

    # Auth (Keycloak). Issuer aliases cover the same realm reached by another host name.
    oidc_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_issuer_aliases: CommaList = []
    # The access tokens' `aud` (Keycloak: an audience mapper on the web client). Required in
    # production, so a token issued to another client of the realm is not accepted.
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    # The admin area (repody.app.admin) manages client companies and their users in Keycloak as
    # the ``repody-admin`` service account; off without its secret. The internal issuer is the
    # realm as the API reaches it (Compose: http://keycloak:8080/realms/repody).
    keycloak_internal_issuer: str | None = None
    # A multi-client installation (the hosted demo): a user outside every client company and not
    # a platform admin gets no permission (repody.infra.auth.user_from_token). Off: a
    # single-client installation, where users need no company.
    require_client_group: bool = False
    keycloak_admin_client_id: str = "repody-admin"
    keycloak_admin_client_secret: SecretStr | None = None

    # Uploads: each file, the files of one run, and the whole request (all files and fields).
    # Keep the web app's proxyClientMaxBodySize (next.config.ts) at max_request_bytes.
    max_upload_bytes: PositiveInt = 25 * 1024 * 1024
    max_upload_files: PositiveInt = 20
    max_request_bytes: PositiveInt = 100 * 1024 * 1024
    upload_allowed_mime_types: CommaList = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
    ]

    # Inference: NuExtract on an OpenAI-compatible server (vLLM on Modal, or a local
    # llama-server).
    inference_base_url: str = "http://127.0.0.1:8081/v1"
    inference_api_key: SecretStr = SecretStr("local")
    inference_model: str = "nuextract3-q8_0"
    inference_timeout_seconds: float = Field(default=180.0, ge=10)
    # Whether /platform/config asks the model server if it is up. Off for an endpoint that scales
    # to zero: the question would start it (and bill it); the model then shows as on demand.
    inference_probe: bool = True
    # Requests in flight per model server: set to its parallel slots (llama-server --parallel).
    # Documents and pages beyond it wait their turn.
    inference_concurrency: PositiveInt = 1

    max_pages_per_document: PositiveInt | None = None
    # Pages one run may send the model, all its documents together (checked before it is
    # queued, from the files' page counts).
    max_pages_per_run: PositiveInt | None = None
    # The longest answer the model may write. Structured answers get less, by their schema's
    # size (repody.extraction.nuextract): an answer that loops stops here, not at the timeout.
    max_output_tokens: PositiveInt = 16_384
    # JSON request bodies (workflow definitions); file uploads have their own limits.
    max_json_bytes: PositiveInt = 2 * 1024 * 1024

    # Credits (repody.app.credits): every run is metered, 1 credit = 1 page sent to the model,
    # plus credit_run_fee per run (the model's start-up and idle time a run causes). Enforced:
    # a run is refused (402) when its account cannot pay its estimate. Accounts are the client
    # companies (Keycloak groups client-<name>); callers outside any client are not charged.
    # Access requests from the site (repody.app.access): off unless set, so an installation never
    # opens a public form it does not use (Repody's own site: the VPS turns it on). Cloudflare
    # Turnstile's secret (no check when unset), and how many requests one network sends an hour.
    access_requests_enabled: bool = False
    turnstile_secret: SecretStr | None = None
    access_requests_per_hour: PositiveInt = 5
    # Declined requests are deleted after this (their details were kept only for the request).
    access_request_retention_days: PositiveInt = 90

    credits_enforced: bool = False
    credit_run_fee: NonNegativeInt = 0
    # The admin area flags a client below this balance; its users see a warning too.
    credit_low_balance: NonNegativeInt = 20
    # For the admin area's spend estimate: what an hour of the model's GPU costs (Modal A10).
    gpu_dollars_per_hour: PositiveFloat = 1.10

    # Runs
    run_timeout_minutes: PositiveInt = 5
    max_queued_runs: NonNegativeInt = 200  # enqueue answers 503 beyond this (0 disables)
    # Runs each workflow API key or signed-in user starts a minute (a Hatchet rate limit: more
    # wait their turn in the queue; 0 disables).
    runs_per_minute_per_client: NonNegativeInt = 600
    # Runs a worker processes at a time (its Hatchet slots).
    worker_concurrency: PositiveInt = 4
    # Runs one client (API key or user) has in progress at once; its other runs wait, taking
    # turns with other clients' (Hatchet round-robin concurrency), so one bulk upload cannot
    # hold every worker slot.
    runs_in_progress_per_client: PositiveInt = 2
    # Finished runs (and their uploaded files) older than this are deleted; 0 keeps them.
    run_retention_days: NonNegativeInt = 0
    # Health probes give up after this long (a hung Postgres reads as down).
    health_timeout_seconds: PositiveFloat = 2.0

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.oidc_enabled and not self.oidc_issuer:
            raise ValueError("AUDIT_OIDC_ISSUER is required when AUDIT_OIDC_ENABLED=true.")
        # Staging is production's rehearsal: the same rules.
        if self.deployment_environment in ("production", "staging"):
            if not self.oidc_enabled:
                raise ValueError("AUDIT_OIDC_ENABLED must be true in production and staging.")
            if not self.oidc_audience:
                raise ValueError("AUDIT_OIDC_AUDIENCE is required in production and staging.")
            turnstile = self.turnstile_secret.get_secret_value() if self.turnstile_secret else ""
            if self.access_requests_enabled and not turnstile:
                raise ValueError(
                    "AUDIT_TURNSTILE_SECRET is required for access requests in production and "
                    "staging: the public form would have no anti-robot check."
                )
        if self.max_upload_bytes > self.max_request_bytes:
            raise ValueError("AUDIT_MAX_UPLOAD_BYTES must fit in AUDIT_MAX_REQUEST_BYTES.")
        if self.inference_timeout_seconds > self.run_timeout_minutes * 60:
            raise ValueError("AUDIT_INFERENCE_TIMEOUT_SECONDS must fit in the run timeout.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
