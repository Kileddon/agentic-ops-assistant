from collections.abc import Mapping, Sequence

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from agentic_ops_assistant.investigation import InvestigationReport, investigate
from agentic_ops_assistant.knowledge.loader import load_articles
from agentic_ops_assistant.knowledge.models import KnowledgeArticle, KnowledgeMatch
from agentic_ops_assistant.operations.status import ServiceStatus
from agentic_ops_assistant.operations.status_loader import load_service_statuses
from agentic_ops_assistant.settings import load_settings


class InvestigationRequest(BaseModel):
    service: str = Field(min_length=1)
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=10)

    @field_validator("service", "query")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Value must not be blank.")

        return normalized_value


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


class InvestigationResponse(BaseModel):
    service: str
    service_status: ServiceStatusResponse | None
    knowledge_matches: list[KnowledgeMatchResponse]


def create_app(
    *,
    articles: Sequence[KnowledgeArticle] = (),
    statuses: Sequence[ServiceStatus] = (),
) -> FastAPI:
    app = FastAPI(
        title="Agentic Ops Assistant",
        version="0.1.0",
    )

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
        )

        return _to_response(report)

    return app


def _to_response(report: InvestigationReport) -> InvestigationResponse:
    return InvestigationResponse(
        service=report.service,
        service_status=_to_status_response(report.service_status),
        knowledge_matches=[_to_match_response(match) for match in report.knowledge_matches],
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


def create_app_from_environment(
    environment: Mapping[str, str] | None = None,
) -> FastAPI:
    settings = load_settings(environment)
    articles = load_articles(settings.knowledge_file)
    statuses = load_service_statuses(settings.service_status_file)

    return create_app(articles=articles, statuses=statuses)
