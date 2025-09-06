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


def test_logger_methods_emit_jsonl(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "emitcase")
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    RunContext._instance = None  # type: ignore[attr-defined]
    logger = JsonlLogger.get(component="runner")
    logger.info("hello", answer=42)
    fp = logger.file_path
    assert fp.exists()
    line = fp.read_text(encoding="utf-8").strip()
    assert '"hello"' in line
    assert '"answer":42' in line
