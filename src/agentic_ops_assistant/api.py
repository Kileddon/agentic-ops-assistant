from collections.abc import Mapping, Sequence
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from agentic_ops_assistant.actions.models import (
    PolicyDecision,
    PolicyStatus,
    ProposedAction,
)
from agentic_ops_assistant.approval.models import ApprovalRequest
from agentic_ops_assistant.approval.store import ApprovalStore, InMemoryApprovalStore
from agentic_ops_assistant.approval.workflow import (
    ApprovalNotFoundError,
    ApprovalService,
)
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
from agentic_ops_assistant.operations.status import ServiceStatus
from agentic_ops_assistant.operations.status_loader import load_service_statuses
from agentic_ops_assistant.settings import load_settings
from agentic_ops_assistant.summarization.client import (
    OllamaSummaryClient,
    SummaryGenerationError,
)
from agentic_ops_assistant.summarization.service import (
    InvestigationSummaryService,
    SummaryClient,
)


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


def create_app(
    *,
    articles: Sequence[KnowledgeArticle] = (),
    statuses: Sequence[ServiceStatus] = (),
    approval_store: ApprovalStore | None = None,
    summary_client: SummaryClient | None = None,
    semantic_embedder: TextEmbedder | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Agentic Ops Assistant",
        version="0.1.0",
    )
    store = InMemoryApprovalStore() if approval_store is None else approval_store
    approval_service = ApprovalService(store)

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

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/investigations", response_model=InvestigationResponse)
    def create_investigation(request: InvestigationRequest) -> InvestigationResponse:
        report = investigate(
            query=request.query,
            service=request.service,
            articles=articles,
            statuses=statuses,
            limit=request.limit,
            semantic_embedder=get_semantic_embedder(request),
        )
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

        return _to_response(report, approval_request)

    @app.post(
        "/investigation-summaries",
        response_model=InvestigationSummaryResponse,
    )
    def create_investigation_summary(
        request: InvestigationRequest,
    ) -> InvestigationSummaryResponse:
        if summary_client is None:
            raise HTTPException(
                status_code=503,
                detail="Local summary service is not configured.",
            )

        report = investigate(
            query=request.query,
            service=request.service,
            articles=articles,
            statuses=statuses,
            limit=request.limit,
            semantic_embedder=get_semantic_embedder(request),
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

        return _to_approval_response(approval_request)

    return app


def create_app_from_environment(
    environment: Mapping[str, str] | None = None,
) -> FastAPI:
    settings = load_settings(environment)
    articles = load_articles(settings.knowledge_file)
    statuses = load_service_statuses(settings.service_status_file)

    return create_app(
        articles=articles,
        statuses=statuses,
        summary_client=OllamaSummaryClient(model=settings.ollama_model),
        semantic_embedder=CachingTextEmbedder(
            OllamaEmbeddingClient(model="nomic-embed-text"),
        ),
    )


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
