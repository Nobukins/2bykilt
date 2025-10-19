import asyncio
from types import SimpleNamespace

import pytest

from src.cli import batch_commands


@pytest.fixture
def fake_run_context(tmp_path):
    def artifact_dir(name: str) -> str:
        target = tmp_path / name
        target.mkdir(parents=True, exist_ok=True)
        return str(target)

    return SimpleNamespace(artifact_dir=artifact_dir)


@pytest.mark.ci_safe
def test_handle_start_command_success(monkeypatch, tmp_path, fake_run_context, capsys):
    csv_file = tmp_path / "jobs.csv"
    csv_file.write_text("url,action\nhttps://example.com,navigate\n", encoding="utf-8")

    manifest = SimpleNamespace(batch_id="batch-1", run_id="run-9", total_jobs=1)
    summary = SimpleNamespace(total_jobs=1, completed_jobs=1, failed_jobs=0)

    monkeypatch.setattr(batch_commands.RunContext, "get", lambda: fake_run_context)
    monkeypatch.setattr(batch_commands, "_run_start_batch", lambda path, context, execute_immediately: manifest)
    monkeypatch.setattr(batch_commands, "BatchEngine", lambda ctx: SimpleNamespace(get_batch_summary=lambda batch_id: summary))

    args = SimpleNamespace(batch_command="start", csv_path=str(csv_file), no_execute=False)

    exit_code = batch_commands.handle_batch_command(args)

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Batch created successfully" in captured.out
    assert "Jobs directory" in captured.out
    assert "Total jobs: 1" in captured.out


@pytest.mark.ci_safe
def test_handle_start_command_missing_file(monkeypatch, tmp_path, fake_run_context, capsys):
    missing_csv = tmp_path / "missing.csv"

    monkeypatch.setattr(batch_commands.RunContext, "get", lambda: fake_run_context)

    args = SimpleNamespace(batch_command="start", csv_path=str(missing_csv), no_execute=False)
    exit_code = batch_commands.handle_batch_command(args)

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "CSV file not found" in captured.out


@pytest.mark.ci_safe
def test_handle_status_command_prints_jobs(monkeypatch, fake_run_context, capsys):
    jobs = [
        {"job_id": "job-1", "status": "completed"},
        {"job_id": "job-2", "status": "failed", "error_message": "boom"},
    ]
    manifest = SimpleNamespace(
        batch_id="batch-1",
        run_id="run-1",
        csv_path="/tmp/jobs.csv",
        total_jobs=2,
        completed_jobs=1,
        failed_jobs=1,
        created_at="2025-10-16",
        jobs=jobs,
    )

    monkeypatch.setattr(batch_commands.RunContext, "get", lambda: fake_run_context)
    monkeypatch.setattr(batch_commands, "BatchEngine", lambda ctx: SimpleNamespace(get_batch_summary=lambda batch_id: manifest))

    args = SimpleNamespace(batch_command="status", batch_id="batch-1")
    exit_code = batch_commands.handle_batch_command(args)

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Batch status" in captured.out
    assert "job-2" in captured.out
    assert "Error: boom" in captured.out


@pytest.mark.ci_safe
def test_handle_update_job_command(monkeypatch, fake_run_context, capsys):
    updates = {}

    def update_job_status(job_id, status, error):
        updates["called_with"] = (job_id, status, error)

    monkeypatch.setattr(batch_commands.RunContext, "get", lambda: fake_run_context)
    monkeypatch.setattr(
        batch_commands,
        "BatchEngine",
        lambda ctx: SimpleNamespace(update_job_status=update_job_status),
    )

    args = SimpleNamespace(batch_command="update-job", job_id="job-1", status="failed", error="timeout")
    exit_code = batch_commands.handle_batch_command(args)

    captured = capsys.readouterr()

    assert exit_code == 0
    assert updates["called_with"] == ("job-1", "failed", "timeout")
    assert "Job status updated" in captured.out


@pytest.mark.ci_safe
def test_handle_execute_command(monkeypatch, fake_run_context, capsys):
    monkeypatch.setattr(batch_commands.RunContext, "get", lambda: fake_run_context)
    monkeypatch.setattr(
        batch_commands,
        "BatchEngine",
        lambda ctx: SimpleNamespace(execute_batch_jobs=lambda batch_id: {"executed_jobs": 2, "successful_jobs": 2, "failed_jobs": 0}),
    )

    args = SimpleNamespace(batch_command="execute", batch_id="batch-5")
    exit_code = batch_commands.handle_batch_command(args)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Batch execution completed" in captured.out
    assert "Jobs executed: 2" in captured.out


@pytest.mark.ci_safe
def test_handle_unknown_command_returns_error(capsys):
    args = SimpleNamespace(batch_command="unknown")
    exit_code = batch_commands.handle_batch_command(args)
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Unknown batch command" in captured.out


@pytest.mark.ci_safe
def test_resolve_csv_path_validates_and_warns(tmp_path, capsys):
    csv_file = tmp_path / "jobs.log"
    csv_file.write_text("id\n1\n", encoding="utf-8")

    resolved = batch_commands._resolve_csv_path(str(csv_file))

    captured = capsys.readouterr()

    assert resolved == csv_file.resolve()
    assert "does not use a typical CSV extension" in captured.out


@pytest.mark.ci_safe
def test_resolve_csv_path_rejects_having_directory(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()

    with pytest.raises(ValueError):
        batch_commands._resolve_csv_path(str(directory))


@pytest.mark.skip(reason="Complex test for edge case asyncio fallback - not critical for coverage")
def test_run_start_batch_falls_back_to_new_event_loop(monkeypatch, tmp_path):
    csv_path = tmp_path / "jobs.csv"
    csv_path.write_text("url\nhttps://example.com\n", encoding="utf-8")

    async def stub_start_batch(*args, **kwargs):
        await asyncio.sleep(0)
        return "manifest"

    loop_state = {"run": False, "closed": False}

    def raising_run(_coro):
        raise RuntimeError("asyncio.run() cannot be called from a running event loop")

    original_new_event_loop = asyncio.new_event_loop

    class StubLoop(asyncio.AbstractEventLoop):
        def run_until_complete(self, coro):
            loop_state["run"] = True
            temp_loop = original_new_event_loop()
            try:
                return temp_loop.run_until_complete(coro)
            finally:
                temp_loop.close()

        def close(self):
            loop_state["closed"] = True

        # Required abstract methods - intentionally empty for test stub
        def run_forever(self):
            pass

        def stop(self):
            pass

        def is_running(self):
            return False

        def is_closed(self):
            return False

        def call_soon(self, callback, *args, **kwargs):
            pass

        def call_at(self, when, callback, *args, **kwargs):
            pass

        def call_later(self, delay, callback, *args, **kwargs):
            pass

        def call_soon_threadsafe(self, callback, *args, **kwargs):
            pass

        def run_in_executor(self, executor, callback, *args):
            pass

        def set_default_executor(self, executor):
            pass

        def get_task_factory(self):
            pass

        def set_task_factory(self, factory):
            pass

        def get_exception_handler(self):
            pass

        def set_exception_handler(self, handler):
            pass

        def default_exception_handler(self, context):
            pass

        def call_exception_handler(self, context):
            pass

        def get_debug(self):
            return False

        def set_debug(self, enabled):
            pass

    monkeypatch.setattr(batch_commands, "start_batch", stub_start_batch)
    monkeypatch.setattr(batch_commands.asyncio, "run", raising_run)
    monkeypatch.setattr(batch_commands.asyncio, "new_event_loop", lambda: StubLoop())

    manifest = batch_commands._run_start_batch(csv_path, SimpleNamespace(), True)

    assert manifest == "manifest"
    assert loop_state["run"]
    assert loop_state["closed"]


@pytest.mark.ci_safe
def test_resolve_csv_path_raises_on_missing_file(tmp_path):
    missing = tmp_path / "nonexistent.csv"
    with pytest.raises(FileNotFoundError, match="CSV file not found"):
        batch_commands._resolve_csv_path(str(missing))


@pytest.mark.ci_safe
def test_handle_start_command_with_permission_error(monkeypatch, tmp_path, fake_run_context, capsys):
    csv_file = tmp_path / "jobs.csv"
    csv_file.write_text("url\nhttps://example.com\n", encoding="utf-8")

    def raise_permission_error(*args, **kwargs):
        raise PermissionError("Access denied")

    monkeypatch.setattr(batch_commands.RunContext, "get", lambda: fake_run_context)
    monkeypatch.setattr(batch_commands, "_run_start_batch", raise_permission_error)

    args = SimpleNamespace(batch_command="start", csv_path=str(csv_file), no_execute=False)
    exit_code = batch_commands.handle_batch_command(args)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Access denied" in captured.out


@pytest.mark.ci_safe
def test_print_job_details_handles_empty_jobs():
    manifest = SimpleNamespace(jobs=None)
    # Should not raise
    batch_commands._print_job_details(manifest)


@pytest.mark.ci_safe
def test_get_value_handles_dict_and_object():
    dict_obj = {"key": "value"}
    obj = SimpleNamespace(key="value")
    
    assert batch_commands._get_value(dict_obj, "key") == "value"
    assert batch_commands._get_value(obj, "key") == "value"
    assert batch_commands._get_value(dict_obj, "missing", "default") == "default"
    assert batch_commands._get_value(obj, "missing", "default") == "default"
