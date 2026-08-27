import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from secrets import compare_digest
from time import perf_counter
from typing import Annotated, Literal, cast
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from agentic_ops_assistant.actions.models import (
    PolicyDecision,
    PolicyStatus,
    ProposedAction,
)
from agentic_ops_assistant.approval.models import ApprovalRequest
from agentic_ops_assistant.approval.store import (
    ApprovalStore,
    InMemoryApprovalStore,
    SqliteApprovalStore,
)
from agentic_ops_assistant.approval.workflow import (
    ApprovalNotFoundError,
    ApprovalService,
)
from agentic_ops_assistant.audit.models import AuditEvent, AuditEventType
from agentic_ops_assistant.audit.service import AuditService
from agentic_ops_assistant.audit.store import (
    AuditStore,
    AuditStoreError,
    InMemoryAuditStore,
    JsonlAuditStore,
)
from agentic_ops_assistant.auth.keycloak import KeycloakJwtAuthenticator
from agentic_ops_assistant.auth.models import ApiRole, Principal
from agentic_ops_assistant.auth.service import StaticApiKeyAuthenticator
from agentic_ops_assistant.embeddings.cache import CachingTextEmbedder
from agentic_ops_assistant.embeddings.client import (
    OllamaEmbeddingClient,
    TextEmbedder,
)
from agentic_ops_assistant.investigation import InvestigationReport, investigate
from agentic_ops_assistant.knowledge.loader import load_articles
from agentic_ops_assistant.knowledge.models import (
    KnowledgeArticle,
    KnowledgeMatch,
    SemanticKnowledgeMatch,
)
from agentic_ops_assistant.notifications.telegram import (
    NotificationSender,
    TelegramNotificationError,
    TelegramNotifier,
)
from agentic_ops_assistant.observability import (
    InMemoryApiMetrics,
    RedisApiMetrics,
    RedisMetricsStore,
    render_prometheus_metrics,
)
from agentic_ops_assistant.operations.prometheus import (
    PrometheusStatusError,
    PrometheusStatusProvider,
)
from agentic_ops_assistant.operations.provider import ServiceStatusProvider
from agentic_ops_assistant.operations.status import ServiceStatus
from agentic_ops_assistant.operations.status_loader import load_service_statuses
from agentic_ops_assistant.rate_limit import FixedWindowRateLimiter, RedisFixedWindowRateLimiter
from agentic_ops_assistant.settings import Settings, SettingsError, load_settings
from agentic_ops_assistant.summarization.client import (
    OllamaSummaryClient,
    SummaryGenerationError,
)
from agentic_ops_assistant.summarization.service import (
    InvestigationSummaryService,
    SummaryClient,
)

_LOGGER = logging.getLogger(__name__)


class InvestigationRequest(BaseModel):
    service: str = Field(min_length=1)
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=10)
    semantic_search: bool = False

    @field_validator("service", "query")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Value must not be blank.")

        return normalized_value


class ApprovalDecisionRequest(BaseModel):
    approved: bool


class ServiceStatusResponse(BaseModel):
    service: str
    health: str
    summary: str


class KnowledgeMatchResponse(BaseModel):
    id: str
    title: str
    content: str
    tags: list[str]
    score: int


class SemanticKnowledgeMatchResponse(BaseModel):
    id: str
    title: str
    content: str
    tags: list[str]
    similarity: float


class ProposedActionResponse(BaseModel):
    service: str
    action_type: str
    rationale: str


class PolicyDecisionResponse(BaseModel):
    status: str
    reason: str


class ApprovalResponse(BaseModel):
    id: UUID
    action: ProposedActionResponse
    status: str


class InvestigationResponse(BaseModel):
    service: str
    service_status: ServiceStatusResponse | None
    knowledge_matches: list[KnowledgeMatchResponse]
    semantic_matches: list[SemanticKnowledgeMatchResponse]
    proposed_action: ProposedActionResponse | None
    policy_decision: PolicyDecisionResponse | None
    approval_request: ApprovalResponse | None


class InvestigationSummaryResponse(BaseModel):
    service: str
    summary: str


class AuditEventResponse(BaseModel):
    id: UUID
    occurred_at: str
    event_type: str
    service: str
    details: dict[str, str]


class ApiMetricsResponse(BaseModel):
    request_count: int
    status_counts: dict[str, int]
    total_duration_ms: float


class PrometheusAlert(BaseModel):
    status: Literal["firing", "resolved"]
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)


class PrometheusAlertWebhook(BaseModel):
    alerts: list[PrometheusAlert]


def create_app(
    *,
    articles: Sequence[KnowledgeArticle] = (),
    statuses: Sequence[ServiceStatus] = (),
    approval_store: ApprovalStore | None = None,
    summary_client: SummaryClient | None = None,
    semantic_embedder: TextEmbedder | None = None,
    status_provider: ServiceStatusProvider | None = None,
    audit_store: AuditStore | None = None,
    authenticator: StaticApiKeyAuthenticator | KeycloakJwtAuthenticator | None = None,
    rate_limiter: FixedWindowRateLimiter | RedisFixedWindowRateLimiter | None = None,
    metrics_store: InMemoryApiMetrics | RedisApiMetrics | None = None,
    prometheus_scrape_token: str | None = None,
    alert_webhook_token: str | None = None,
    alert_notifier: NotificationSender | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Agentic Ops Assistant",
        version="0.1.0",
    )
    store = InMemoryApprovalStore() if approval_store is None else approval_store
    approval_service = ApprovalService(store)
    event_store = InMemoryAuditStore() if audit_store is None else audit_store
    audit_service = AuditService(event_store)
    metrics = InMemoryApiMetrics() if metrics_store is None else metrics_store

    @app.middleware("http")
    async def add_request_observability(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        started_at = perf_counter()
        response = await call_next(request)
        duration_ms = (perf_counter() - started_at) * 1000
        metrics.record(status_code=response.status_code, duration_ms=duration_ms)
        response.headers["X-Request-ID"] = request_id
        _LOGGER.info(
            "request_completed path=%s status=%s duration_ms=%.1f request_id=%s",
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response

    def require_role(endpoint: str, *allowed_roles: ApiRole) -> Callable[..., Principal]:
        def dependency(
            api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
            authorization: Annotated[str | None, Header()] = None,
        ) -> Principal:
            if authenticator is None:
                return Principal(ApiRole.OPERATOR)

            credential = _credential_from_headers(authenticator, api_key, authorization)

            if credential is None:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication credentials are required.",
                    headers={"WWW-Authenticate": _authentication_scheme(authenticator)},
                )

            principal = authenticator.authenticate(credential)

            if principal is None:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials.",
                    headers={"WWW-Authenticate": _authentication_scheme(authenticator)},
                )

            if principal.role not in allowed_roles:
                raise HTTPException(status_code=403, detail="Insufficient API role.")

            if rate_limiter is not None:
                retry_after = rate_limiter.acquire(role=principal.role, endpoint=endpoint)

                if retry_after is not None:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded.",
                        headers={"Retry-After": str(retry_after)},
                    )

            return principal

        return dependency

    def get_semantic_embedder(
        request: InvestigationRequest,
    ) -> TextEmbedder | None:
        if not request.semantic_search:
            return None

        if semantic_embedder is None:
            raise HTTPException(
                status_code=503,
                detail="Local semantic search is not configured.",
            )

        return semantic_embedder

    def build_report(
        request: InvestigationRequest,
        principal: Principal,
    ) -> InvestigationReport:
        try:
            return investigate(
                query=request.query,
                service=request.service,
                articles=articles,
                statuses=statuses,
                limit=request.limit,
                semantic_embedder=get_semantic_embedder(request),
                status_provider=status_provider,
            )
        except PrometheusStatusError as error:
            record_event(
                AuditEventType.STATUS_PROVIDER_FAILED,
                request.service,
                {"actor_role": principal.role.value, "provider": "prometheus"},
            )
            raise HTTPException(status_code=503, detail=str(error)) from error

    def record_event(
        event_type: AuditEventType,
        service: str,
        details: Mapping[str, str],
    ) -> AuditEvent:
        try:
            return audit_service.record(event_type, service, details)
        except AuditStoreError as error:
            raise HTTPException(
                status_code=503,
                detail="Audit storage is unavailable.",
            ) from error

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/investigations", response_model=InvestigationResponse)
    def create_investigation(
        request: InvestigationRequest,
        principal: Annotated[Principal, Depends(require_role("investigations", ApiRole.OPERATOR))],
    ) -> InvestigationResponse:
        report = build_report(request, principal)
        approval_request: ApprovalRequest | None = None

        if (
            report.proposed_action is not None
            and report.policy_decision is not None
            and report.policy_decision.status is PolicyStatus.REQUIRES_APPROVAL
        ):
            approval_request = approval_service.create(
                report.proposed_action,
                report.policy_decision,
            )
            record_event(
                AuditEventType.APPROVAL_CREATED,
                report.service,
                {
                    "action_type": report.proposed_action.action_type.value,
                    "actor_role": principal.role.value,
                    "approval_id": str(approval_request.id),
                },
            )

        record_event(
            AuditEventType.INVESTIGATION_CREATED,
            report.service,
            {
                "keyword_match_count": str(len(report.knowledge_matches)),
                "actor_role": principal.role.value,
                "semantic_match_count": str(len(report.semantic_matches)),
                "policy_status": (
                    report.policy_decision.status.value
                    if report.policy_decision is not None
                    else "none"
                ),
            },
        )

        return _to_response(report, approval_request)

    @app.post(
        "/investigation-summaries",
        response_model=InvestigationSummaryResponse,
    )
    def create_investigation_summary(
        request: InvestigationRequest,
        principal: Annotated[
            Principal,
            Depends(require_role("investigation-summaries", ApiRole.OPERATOR)),
        ],
    ) -> InvestigationSummaryResponse:
        if summary_client is None:
            raise HTTPException(
                status_code=503,
                detail="Local summary service is not configured.",
            )

        report = build_report(request, principal)

        record_event(
            AuditEventType.INVESTIGATION_CREATED,
            report.service,
            {
                "keyword_match_count": str(len(report.knowledge_matches)),
                "actor_role": principal.role.value,
                "semantic_match_count": str(len(report.semantic_matches)),
                "policy_status": (
                    report.policy_decision.status.value
                    if report.policy_decision is not None
                    else "none"
                ),
            },
        )

        try:
            summary = InvestigationSummaryService(summary_client).summarize(report)
        except SummaryGenerationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

        return InvestigationSummaryResponse(
            service=report.service,
            summary=summary,
        )

    @app.post(
        "/approvals/{approval_id}/decisions",
        response_model=ApprovalResponse,
    )
    def decide_pending_approval(
        approval_id: UUID,
        request: ApprovalDecisionRequest,
        principal: Annotated[
            Principal,
            Depends(require_role("approval-decisions", ApiRole.APPROVER)),
        ],
    ) -> ApprovalResponse:
        try:
            approval_request = approval_service.decide(
                approval_id,
                approved=request.approved,
            )
        except ApprovalNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        record_event(
            AuditEventType.APPROVAL_DECIDED,
            approval_request.action.service,
            {
                "approval_id": str(approval_request.id),
                "actor_role": principal.role.value,
                "status": approval_request.status.value,
            },
        )

        return _to_approval_response(approval_request)

    @app.get("/audit-events", response_model=list[AuditEventResponse])
    def list_audit_events(
        principal: Annotated[Principal, Depends(require_role("audit-events", ApiRole.AUDITOR))],
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[AuditEventResponse]:
        try:
            events = audit_service.list_events(limit)
        except AuditStoreError as error:
            raise HTTPException(
                status_code=503,
                detail="Audit storage is unavailable.",
            ) from error

        return [_to_audit_event_response(event) for event in events]

    @app.get("/metrics", response_model=ApiMetricsResponse)
    def get_metrics(
        principal: Annotated[Principal, Depends(require_role("metrics", ApiRole.AUDITOR))],
    ) -> ApiMetricsResponse:
        snapshot = metrics.snapshot()
        return ApiMetricsResponse(
            request_count=snapshot.request_count,
            status_counts=snapshot.status_counts,
            total_duration_ms=snapshot.total_duration_ms,
        )

    @app.get("/metrics/prometheus", response_class=PlainTextResponse)
    def get_prometheus_metrics(
        authorization: Annotated[str | None, Header()] = None,
    ) -> PlainTextResponse:
        if prometheus_scrape_token is None:
            raise HTTPException(status_code=503, detail="Prometheus scrape is not configured.")

        expected_header = f"Bearer {prometheus_scrape_token}"
        if authorization is None or not compare_digest(authorization, expected_header):
            raise HTTPException(status_code=401, detail="Invalid Prometheus scrape credentials.")

        return PlainTextResponse(render_prometheus_metrics(metrics.snapshot()))

    @app.post("/alerts/prometheus")
    def receive_prometheus_alert(
        webhook: PrometheusAlertWebhook,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, int]:
        if alert_webhook_token is None or alert_notifier is None:
            raise HTTPException(
                status_code=503, detail="Prometheus alert notifications are not configured."
            )

        expected_header = f"Bearer {alert_webhook_token}"
        if authorization is None or not compare_digest(authorization, expected_header):
            raise HTTPException(status_code=401, detail="Invalid Prometheus alert credentials.")

        firing_alerts = tuple(alert for alert in webhook.alerts if alert.status == "firing")
        try:
            for alert in firing_alerts:
                alert_notifier.send(_format_prometheus_alert(alert))
        except TelegramNotificationError as error:
            raise HTTPException(
                status_code=502, detail="Telegram alert notification failed."
            ) from error

        return {"notified": len(firing_alerts)}

    return app


def create_app_from_environment(
    environment: Mapping[str, str] | None = None,
) -> FastAPI:
    settings = load_settings(environment)
    articles = load_articles(settings.knowledge_file)

    statuses: tuple[ServiceStatus, ...] = ()
    status_provider: ServiceStatusProvider | None = None

    if settings.status_source == "json":
        if settings.service_status_file is None:
            raise RuntimeError("JSON status source requires a status file.")

        statuses = load_service_statuses(settings.service_status_file)
    else:
        if settings.prometheus_url is None:
            raise RuntimeError("Prometheus status source requires a URL.")

        status_provider = PrometheusStatusProvider(settings.prometheus_url)

    return create_app(
        articles=articles,
        statuses=statuses,
        summary_client=OllamaSummaryClient(model=settings.ollama_model),
        semantic_embedder=CachingTextEmbedder(
            OllamaEmbeddingClient(model="nomic-embed-text"),
        ),
        status_provider=status_provider,
        audit_store=JsonlAuditStore(settings.audit_log_file),
        approval_store=SqliteApprovalStore(str(settings.approval_database_file)),
        authenticator=_authenticator_from_settings(settings),
        rate_limiter=_rate_limiter_from_settings(settings),
        metrics_store=_metrics_from_settings(settings),
        prometheus_scrape_token=settings.prometheus_scrape_token,
        alert_webhook_token=settings.alert_webhook_token,
        alert_notifier=_alert_notifier_from_settings(settings),
    )


def _rate_limiter_from_settings(
    settings: Settings,
) -> FixedWindowRateLimiter | RedisFixedWindowRateLimiter:
    if settings.redis_url is not None:
        import redis

        return RedisFixedWindowRateLimiter(
            redis.Redis.from_url(settings.redis_url, decode_responses=True),
            max_requests=settings.rate_limit_requests,
            window_seconds=int(settings.rate_limit_window_seconds),
        )

    return FixedWindowRateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )


def _metrics_from_settings(settings: Settings) -> InMemoryApiMetrics | RedisApiMetrics:
    if settings.redis_url is not None:
        import redis

        return RedisApiMetrics(
            cast(
                RedisMetricsStore,
                redis.Redis.from_url(settings.redis_url, decode_responses=True),
            ),
        )

    return InMemoryApiMetrics()


def _alert_notifier_from_settings(settings: Settings) -> TelegramNotifier | None:
    if settings.alert_webhook_token is None:
        return None

    if settings.telegram_bot_token is None:
        raise SettingsError("Missing required environment variable: OPS_TELEGRAM_BOT_TOKEN")

    if settings.telegram_chat_id is None:
        raise SettingsError("Missing required environment variable: OPS_TELEGRAM_CHAT_ID")

    return TelegramNotifier(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )


def _authenticator_from_settings(
    settings: Settings,
) -> StaticApiKeyAuthenticator | KeycloakJwtAuthenticator:
    if settings.keycloak_issuer is not None or settings.keycloak_audience is not None:
        if settings.keycloak_issuer is None:
            raise SettingsError("Missing required environment variable: OPS_KEYCLOAK_ISSUER")

        if settings.keycloak_audience is None:
            raise SettingsError("Missing required environment variable: OPS_KEYCLOAK_AUDIENCE")

        return KeycloakJwtAuthenticator(
            issuer=settings.keycloak_issuer,
            audience=settings.keycloak_audience,
        )

    if settings.operator_api_key is None:
        raise SettingsError("Missing required environment variable: OPS_OPERATOR_API_KEY")

    if settings.approver_api_key is None:
        raise SettingsError("Missing required environment variable: OPS_APPROVER_API_KEY")

    if settings.auditor_api_key is None:
        raise SettingsError("Missing required environment variable: OPS_AUDITOR_API_KEY")

    return StaticApiKeyAuthenticator(
        operator_key=settings.operator_api_key,
        approver_key=settings.approver_api_key,
        auditor_key=settings.auditor_api_key,
        operator_next_key=settings.operator_next_api_key,
        approver_next_key=settings.approver_next_api_key,
        auditor_next_key=settings.auditor_next_api_key,
    )


def _credential_from_headers(
    authenticator: StaticApiKeyAuthenticator | KeycloakJwtAuthenticator,
    api_key: str | None,
    authorization: str | None,
) -> str | None:
    if isinstance(authenticator, StaticApiKeyAuthenticator):
        return api_key

    if authorization is None or not authorization.startswith("Bearer "):
        return None

    return authorization.removeprefix("Bearer ").strip() or None


def _authentication_scheme(
    authenticator: StaticApiKeyAuthenticator | KeycloakJwtAuthenticator,
) -> str:
    if isinstance(authenticator, StaticApiKeyAuthenticator):
        return "ApiKey"

    return "Bearer"


def _format_prometheus_alert(alert: PrometheusAlert) -> str:
    alert_name = alert.labels.get("alertname", "Prometheus alert")
    service = alert.labels.get("service") or alert.labels.get("job", "unknown service")
    summary = alert.annotations.get("summary", "No summary provided.")
    return f"Prometheus alert: {alert_name}\nService: {service}\nSummary: {summary}"


def _to_response(
    report: InvestigationReport,
    approval_request: ApprovalRequest | None,
) -> InvestigationResponse:
    return InvestigationResponse(
        service=report.service,
        service_status=_to_status_response(report.service_status),
        knowledge_matches=[_to_match_response(match) for match in report.knowledge_matches],
        semantic_matches=[_to_semantic_match_response(match) for match in report.semantic_matches],
        proposed_action=_to_action_response(report.proposed_action),
        policy_decision=_to_policy_response(report.policy_decision),
        approval_request=(
            _to_approval_response(approval_request) if approval_request is not None else None
        ),
    )


def _to_status_response(status: ServiceStatus | None) -> ServiceStatusResponse | None:
    if status is None:
        return None

    return ServiceStatusResponse(
        service=status.service,
        health=status.health.value,
        summary=status.summary,
    )


def _to_match_response(match: KnowledgeMatch) -> KnowledgeMatchResponse:
    return KnowledgeMatchResponse(
        id=match.article.id,
        title=match.article.title,
        content=match.article.content,
        tags=list(match.article.tags),
        score=match.score,
    )


def _to_semantic_match_response(
    match: SemanticKnowledgeMatch,
) -> SemanticKnowledgeMatchResponse:
    return SemanticKnowledgeMatchResponse(
        id=match.article.id,
        title=match.article.title,
        content=match.article.content,
        tags=list(match.article.tags),
        similarity=match.similarity,
    )


def _to_action_response(
    action: ProposedAction | None,
) -> ProposedActionResponse | None:
    if action is None:
        return None

    return ProposedActionResponse(
        service=action.service,
        action_type=action.action_type.value,
        rationale=action.rationale,
    )


def _to_policy_response(
    decision: PolicyDecision | None,
) -> PolicyDecisionResponse | None:
    if decision is None:
        return None

    return PolicyDecisionResponse(
        status=decision.status.value,
        reason=decision.reason,
    )


def _to_approval_response(
    approval_request: ApprovalRequest,
) -> ApprovalResponse:
    return ApprovalResponse(
        id=approval_request.id,
        action=ProposedActionResponse(
            service=approval_request.action.service,
            action_type=approval_request.action.action_type.value,
            rationale=approval_request.action.rationale,
        ),
        status=approval_request.status.value,
    )


def _to_audit_event_response(event: AuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        id=event.id,
        occurred_at=event.occurred_at.isoformat(),
        event_type=event.event_type.value,
        service=event.service,
        details=dict(event.details),
    )
