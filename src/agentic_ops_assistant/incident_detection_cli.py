import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from agentic_ops_assistant.embeddings.cache import CachingTextEmbedder
from agentic_ops_assistant.embeddings.client import OllamaEmbeddingClient
from agentic_ops_assistant.incidents.notifications import format_incident_notification
from agentic_ops_assistant.incidents.prometheus import (
    PrometheusIncidentDetector,
    PrometheusInstantQueryClient,
)
from agentic_ops_assistant.incidents.service import IncidentInvestigationService
from agentic_ops_assistant.knowledge.loader import KnowledgeLoadError, load_articles
from agentic_ops_assistant.notifications.telegram import TelegramNotificationError, TelegramNotifier
from agentic_ops_assistant.operations.prometheus import (
    PrometheusStatusError,
    PrometheusStatusProvider,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        articles = load_articles(args.knowledge_file)
        status_provider = PrometheusStatusProvider(args.prometheus_url)
        detector = PrometheusIncidentDetector(
            status_provider=status_provider,
            query_client=PrometheusInstantQueryClient(args.prometheus_url),
            latency_threshold_ms=args.latency_threshold_ms,
        )
        service = IncidentInvestigationService(
            detector=detector,
            articles=articles,
            status_provider=status_provider,
            semantic_embedder=(
                CachingTextEmbedder(OllamaEmbeddingClient(model=args.embedding_model))
                if args.semantic_search
                else None
            ),
        )
        incidents = service.investigate(args.service, semantic_search=args.semantic_search)
        notifier = _notifier_from_environment(args.notify)
    except (KnowledgeLoadError, PrometheusStatusError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if not incidents:
        print(f"No incident signals detected for {args.service}.")
        return 0

    try:
        for incident in incidents:
            message = format_incident_notification(incident)
            print(message)
            if notifier is not None:
                notifier.send(message)
    except TelegramNotificationError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ops-detect-incidents",
        description="Detect Prometheus incident signals and build investigations.",
    )
    parser.add_argument("service")
    parser.add_argument("--knowledge-file", required=True, type=Path)
    parser.add_argument("--prometheus-url", required=True)
    parser.add_argument("--semantic-search", action="store_true")
    parser.add_argument("--embedding-model", default="nomic-embed-text")
    parser.add_argument("--latency-threshold-ms", type=float, default=1_000.0)
    parser.add_argument("--notify", action="store_true")
    return parser


def _notifier_from_environment(notify: bool) -> TelegramNotifier | None:
    if not notify:
        return None

    bot_token = os.environ.get("OPS_TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("OPS_TELEGRAM_CHAT_ID")
    if bot_token is None or chat_id is None:
        raise ValueError(
            "OPS_TELEGRAM_BOT_TOKEN and OPS_TELEGRAM_CHAT_ID are required with --notify."
        )

    return TelegramNotifier(bot_token=bot_token, chat_id=chat_id)


if __name__ == "__main__":
    raise SystemExit(main())
