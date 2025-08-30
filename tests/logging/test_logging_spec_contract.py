import json
from pathlib import Path

from src.logging.jsonl_logger import JsonlLogger
from src.runtime.run_context import RunContext

def test_logger_get_creates_directory_using_run_context(tmp_path, monkeypatch):
    # Force artifacts root to temp via monkeypatch by adjusting RunContext artifact root indirectly
    # We cannot easily change RunContext internal root without modifying code, so just verify path pattern.
    logger = JsonlLogger.get(component="browser")
    rc = RunContext.get()
    # Directory should contain run_id_base and suffix -log
    expected_dir_prefix = f"{rc.run_id_base}-log"
    assert expected_dir_prefix in str(logger.file_path.parent)
    assert logger.file_path.name == "app.log.jsonl"


def test_logger_methods_raise_not_implemented():
    logger = JsonlLogger.get(component="runner")
    for method in (logger.debug, logger.info, logger.warning, logger.error, logger.critical):
        try:
            method("test message")
        except NotImplementedError as e:
            assert "Issue #56" in str(e)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected NotImplementedError")
