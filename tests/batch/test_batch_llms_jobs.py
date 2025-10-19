from unittest.mock import AsyncMock, Mock

import pytest

from src.batch.engine import BatchEngine, BatchJob
from src.runtime.run_context import RunContext


@pytest.mark.ci_safe
@pytest.mark.asyncio
async def test_batch_engine_runs_registered_llms_jobs(monkeypatch, tmp_path):
    run_context = Mock(spec=RunContext)
    run_context.run_id_base = "test-run"
    run_context.artifact_dir.side_effect = lambda component: tmp_path / f"{run_context.run_id_base}-{component}"

    engine = BatchEngine(run_context)

    direct_control_mock = AsyncMock(return_value={"status": "ok"})
    monkeypatch.setattr(
        "src.modules.direct_browser_control.execute_direct_browser_control",
        direct_control_mock,
    )

    run_script_mock = AsyncMock(return_value=("Action runner executed successfully", None))
    monkeypatch.setattr("src.script.script_manager.run_script", run_script_mock)

    jobs = [
        BatchJob(job_id="job-1", run_id="run", row_data={"task": "@get-title"}),
        BatchJob(job_id="job-2", run_id="run", row_data={"task": "@demo-artifact-capture"}),
        BatchJob(
            job_id="job-3",
            run_id="run",
            row_data={"task": "@nogtips-artifact-capture", "params.query": "LLMs.txt"},
        ),
    ]

    statuses = []
    for job in jobs:
        status = await engine.execute_job_with_retry(job, max_retries=0)
        statuses.append(status)

    assert statuses == ["completed", "completed", "completed"]

    direct_control_mock.assert_awaited_once()
    assert direct_control_mock.await_args[0][0]["name"] == "get-title"

    assert run_script_mock.await_count == 2
    called_action_names = [call.args[0]["name"] for call in run_script_mock.await_args_list]
    assert "demo-artifact-capture" in called_action_names
    assert "nogtips-artifact-capture" in called_action_names

    final_call = run_script_mock.await_args_list[-1]
    assert final_call.args[1]["query"] == "LLMs.txt"
