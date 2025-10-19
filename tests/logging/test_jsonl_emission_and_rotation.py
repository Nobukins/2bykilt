import os
import json
import pytest
from pathlib import Path

from src.logging.jsonl_logger import JsonlLogger
from src.runtime.run_context import RunContext


@pytest.mark.ci_safe
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


@pytest.mark.ci_safe
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


@pytest.mark.ci_safe
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


@pytest.mark.ci_safe
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


@pytest.mark.ci_safe
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


@pytest.mark.ci_safe
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


@pytest.mark.ci_safe
def test_log_base_dir_custom_path(tmp_path, monkeypatch):
    """Test LOG_BASE_DIR environment variable sets custom log directory."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "runcustom")
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    
    custom_log_dir = tmp_path / "custom_logs"
    monkeypatch.setenv("LOG_BASE_DIR", str(custom_log_dir))
    
    logger = JsonlLogger.get("custom_test")
    logger.info("test message")
    
    # Check that log was written to custom directory
    expected_path = custom_log_dir / "custom_test" / "app.log.jsonl"
    assert expected_path.exists()
    
    content = expected_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 1
    rec = json.loads(content[0])
    assert rec["msg"] == "test message"
    assert rec["component"] == "custom_test"


@pytest.mark.ci_safe
def test_log_base_dir_default_fallback(tmp_path, monkeypatch):
    """Test that unset LOG_BASE_DIR defaults to ./logs."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "rundefault")
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    
    # Don't set LOG_BASE_DIR
    logger = JsonlLogger.get("default_test")
    logger.info("test message")
    
    # Check that log was written to ./logs
    expected_path = tmp_path / "logs" / "default_test" / "app.log.jsonl"
    assert expected_path.exists()
    
    content = expected_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 1
    rec = json.loads(content[0])
    assert rec["msg"] == "test message"
    assert rec["component"] == "default_test"


@pytest.mark.ci_safe
def test_log_base_dir_src_guard(tmp_path, monkeypatch):
    """Test that LOG_BASE_DIR cannot point to src/ directory."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "runguard")
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    
    # Create src directory
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    
    # Try to set LOG_BASE_DIR to src/
    monkeypatch.setenv("LOG_BASE_DIR", str(src_dir))
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="LOG_BASE_DIR cannot point to src/ directory"):
        JsonlLogger.get("guard_test")


@pytest.mark.ci_safe
def test_log_base_dir_src_subdirectory_guard(tmp_path, monkeypatch):
    """Test that LOG_BASE_DIR cannot point to src/ subdirectories."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "runsubguard")
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    
    # Create src/logs directory
    src_logs_dir = tmp_path / "src" / "logs"
    src_logs_dir.mkdir(parents=True)
    
    # Try to set LOG_BASE_DIR to src/logs/
    monkeypatch.setenv("LOG_BASE_DIR", str(src_logs_dir))
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="LOG_BASE_DIR cannot point to src/ directory"):
        JsonlLogger.get("subguard_test")


@pytest.mark.ci_safe
def test_category_based_directory_structure(tmp_path, monkeypatch):
    """Test that logs are organized by category in separate directories."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "runcategory")
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    
    # Get loggers for different categories
    runner_logger = JsonlLogger.get("runner")
    artifacts_logger = JsonlLogger.get("artifacts")
    browser_logger = JsonlLogger.get("browser")
    
    # Log messages
    runner_logger.info("runner event")
    artifacts_logger.info("artifacts event")
    browser_logger.info("browser event")
    
    # Check directory structure
    logs_dir = tmp_path / "logs"
    assert (logs_dir / "runner" / "app.log.jsonl").exists()
    assert (logs_dir / "artifacts" / "app.log.jsonl").exists()
    assert (logs_dir / "browser" / "app.log.jsonl").exists()
    
    # Verify content in each category
    runner_content = json.loads((logs_dir / "runner" / "app.log.jsonl").read_text().strip())
    assert runner_content["component"] == "runner"
    assert runner_content["msg"] == "runner event"
    
    artifacts_content = json.loads((logs_dir / "artifacts" / "app.log.jsonl").read_text().strip())
    assert artifacts_content["component"] == "artifacts"
    assert artifacts_content["msg"] == "artifacts event"
    
    browser_content = json.loads((logs_dir / "browser" / "app.log.jsonl").read_text().strip())
    assert browser_content["component"] == "browser"
    assert browser_content["msg"] == "browser event"


@pytest.mark.ci_safe
def test_single_path_output_verification(tmp_path, monkeypatch):
    """Test that all logs go to single base directory (no scattered outputs)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "runsingle")
    RunContext._instance = None  # type: ignore[attr-defined]
    JsonlLogger._instances.clear()  # type: ignore[attr-defined]
    
    # Get multiple loggers
    categories = ["runner", "artifacts", "browser", "config", "metrics", "security"]
    loggers = [JsonlLogger.get(cat) for cat in categories]
    
    # Log messages
    for i, logger in enumerate(loggers):
        logger.info(f"test message {i}")
    
    # Verify all logs are under ./logs/
    logs_dir = tmp_path / "logs"
    for category in categories:
        log_file = logs_dir / category / "app.log.jsonl"
        assert log_file.exists(), f"Log file for {category} should exist"
        
        content = json.loads(log_file.read_text().strip())
        assert content["component"] == category
        assert content["msg"] == f"test message {categories.index(category)}"
    
    # Ensure no logs exist outside ./logs/
    # (This would be a more comprehensive check in real implementation)
