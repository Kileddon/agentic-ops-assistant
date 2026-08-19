from pytest import CaptureFixture

from agentic_ops_assistant.cli import main


def test_main_prints_matching_article(capsys: CaptureFixture[str]) -> None:
    exit_code = main(["database", "timeout"])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "[score=2] Database timeout" in output


def test_main_reports_empty_result(capsys: CaptureFixture[str]) -> None:
    exit_code = main(["network"])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert output == "No matching articles found.\n"
