import os
import json
from pathlib import Path

from src.logging.jsonl_logger import JsonlLogger
from src.runtime.run_context import RunContext


def test_basic_emission(tmp_path, monkeypatch):
    # Direct artifacts into tmp by changing CWD (RunContext uses relative path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "runbasic")
    # Reset singletons for isolation
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    logger = JsonlLogger.get("core")
    logger.info("hello", foo=1)
    fp = logger.file_path
    assert fp.exists()
    content = fp.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 1
    rec = json.loads(content[0])
    assert rec["msg"] == "hello"
    assert rec["foo"] == 1
    assert rec["component"] == "core"
    assert rec["seq"] == 1


def test_rotation_and_retention(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "runrotate")
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    monkeypatch.setenv("BYKILT_LOG_MAX_SIZE", "200")  # small size
    monkeypatch.setenv("BYKILT_LOG_MAX_FILES", "3")
    logger = JsonlLogger.get("rot")
    # Write enough lines to exceed size multiple times
    for i in range(120):
        logger.info("line", i=i, payload="x" * 10)
    fp = logger.file_path
    # Active file exists
    assert fp.exists()
    # Rotated files .1 .2 .3 bounded
    rotated = [fp.with_name(fp.name + f".{n}") for n in (1, 2, 3, 4, 5)]
    assert rotated[0].exists()  # .1
    assert rotated[1].exists()  # .2
    assert rotated[2].exists()  # .3
    # .4 should NOT exist due to retention 3
    assert not rotated[3].exists()

    # Ensure no file grew absurdly large (basic guard)
    for r in [fp] + rotated[:3]:
        if r.exists():
            assert r.stat().st_size <= 400  # some slack


def test_log_level_filtering(tmp_path, monkeypatch):
    """Test that LOG_LEVEL environment variable filters log messages correctly."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "runlevel")
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    
    # Test with LOG_LEVEL=INFO (default)
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    logger = JsonlLogger.get("level_test")
    
    # Log messages at different levels
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")
    
    fp = logger.file_path
    content = fp.read_text(encoding="utf-8").strip().splitlines()
    
    # Should have 4 messages (INFO, WARNING, ERROR, CRITICAL) - DEBUG filtered out
    assert len(content) == 4
    messages = [json.loads(line)["msg"] for line in content]
    assert "debug message" not in messages
    assert "info message" in messages
    assert "warning message" in messages
    assert "error message" in messages
    assert "critical message" in messages


def test_log_level_debug(tmp_path, monkeypatch):
    """Test that LOG_LEVEL=DEBUG allows all messages through."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "rundebug")
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    logger = JsonlLogger.get("debug_test")
    
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    
    fp = logger.file_path
    content = fp.read_text(encoding="utf-8").strip().splitlines()
    
    # Should have all 3 messages
    assert len(content) == 3
    messages = [json.loads(line)["msg"] for line in content]
    assert "debug message" in messages
    assert "info message" in messages
    assert "warning message" in messages


def test_log_level_error(tmp_path, monkeypatch):
    """Test that LOG_LEVEL=ERROR filters out WARNING and below."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "runerror")
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    logger = JsonlLogger.get("error_test")
    
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")
    
    fp = logger.file_path
    content = fp.read_text(encoding="utf-8").strip().splitlines()
    
    # Should have 2 messages (ERROR, CRITICAL) - WARNING and below filtered out
    assert len(content) == 2
    messages = [json.loads(line)["msg"] for line in content]
    assert "debug message" not in messages
    assert "info message" not in messages
    assert "warning message" not in messages
    assert "error message" in messages
    assert "critical message" in messages


def test_log_level_invalid_defaults_to_info(tmp_path, monkeypatch):
    """Test that invalid LOG_LEVEL defaults to INFO."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "runinvalid")
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    
    monkeypatch.setenv("LOG_LEVEL", "INVALID_LEVEL")
    logger = JsonlLogger.get("invalid_test")
    
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    
    fp = logger.file_path
    content = fp.read_text(encoding="utf-8").strip().splitlines()
    
    # Should behave like INFO level (DEBUG filtered out)
    assert len(content) == 2
    messages = [json.loads(line)["msg"] for line in content]
    assert "debug message" not in messages
    assert "info message" in messages
    assert "warning message" in messages
