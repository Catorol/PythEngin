import logging

import pytest

from research_graph.logging_setup import setup_logging


def test_repeated_call_does_not_duplicate_handlers() -> None:
    setup_logging("INFO")
    setup_logging("INFO")
    assert len(logging.getLogger().handlers) == 1


def test_writes_to_stderr_not_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging("INFO")
    logging.getLogger("my.logger").info("hello world")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "hello world" in captured.err


def test_format_has_level_name_and_message(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging("INFO")
    logging.getLogger("my.logger").warning("careful")
    err = capsys.readouterr().err
    assert "WARNING" in err
    assert "my.logger" in err
    assert "careful" in err


def test_level_filters_messages(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging("WARNING")
    logger = logging.getLogger("my.logger")
    logger.info("hidden")
    logger.warning("shown")
    err = capsys.readouterr().err
    assert "hidden" not in err
    assert "shown" in err


def test_noisy_libraries_are_quieted() -> None:
    setup_logging("DEBUG")
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("urllib3").level == logging.WARNING
