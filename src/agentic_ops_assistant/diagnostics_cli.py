import argparse
import os
from collections.abc import Sequence

from agentic_ops_assistant.diagnostics.docker import DiagnosticsError, DockerDiagnosticsCollector
from agentic_ops_assistant.diagnostics.logs import search_log_lines
from agentic_ops_assistant.notifications.telegram import TelegramNotificationError, TelegramNotifier


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect read-only Docker diagnostics.")
    parser.add_argument("container")
    parser.add_argument("--search", help="Find matching terms in the collected log lines.")
    parsed_arguments = parser.parse_args(arguments)

    try:
        diagnostics = DockerDiagnosticsCollector(allowed_container="demo-api").collect(
            parsed_arguments.container,
        )
    except DiagnosticsError as error:
        print(f"Error: {error}")
        return 1

    print(diagnostics.telegram_summary())
    if parsed_arguments.search is None:
        if diagnostics.recent_logs:
            print("Recent logs:")
            print("\n".join(diagnostics.recent_logs))
    else:
        try:
            matches = search_log_lines(diagnostics.recent_logs, parsed_arguments.search)
        except ValueError as error:
            print(f"Error: {error}")
            return 2

        print("Matching logs:")
        print("\n".join(matches) if matches else "No matching log lines found.")

    bot_token = os.environ.get("OPS_TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("OPS_TELEGRAM_CHAT_ID")
    if (bot_token is None) != (chat_id is None):
        print("Error: Both Telegram environment variables must be configured together.")
        return 2
    if bot_token is not None and chat_id is not None:
        try:
            TelegramNotifier(bot_token=bot_token, chat_id=chat_id).send(
                diagnostics.telegram_summary()
            )
        except TelegramNotificationError as error:
            print(f"Error: {error}")
            return 1
    return 0
