"""Batch command CLI interface for bykilt.

This module handles batch execution commands through the CLI.
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.batch.engine import BatchEngine, start_batch
from src.runtime.run_context import RunContext

logger = logging.getLogger(__name__)


CSV_SUFFIXES = {".csv", ".txt"}


def _resolve_csv_path(csv_path: str) -> Path:
    """Validate and resolve a CSV path supplied via the CLI.
    
    Args:
        csv_path: User-supplied path string
        
    Returns:
        Resolved Path object
        
    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If path is not a file
    """
    candidate = Path(csv_path).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as error:
        logger.error("CSV file not found: %s", candidate)
        raise FileNotFoundError(f"CSV file not found: {candidate}") from error
    
    if not resolved.is_file():
        logger.error("Path is not a file: %s", resolved)
        raise ValueError(f"Path is not a file: {resolved}")
    
    if resolved.suffix.lower() not in CSV_SUFFIXES:
        logger.warning("File %s does not use a typical CSV extension", resolved.name)
        print(f"⚠️ Warning: {resolved.name} does not use a typical CSV extension")
    
    logger.debug("Resolved CSV path: %s", resolved)
    return resolved


def _cancel_all_tasks(loop):
    """Cancel all pending tasks in the event loop."""
    try:
        to_cancel = asyncio.all_tasks(loop)
        if not to_cancel:
            return

        for task in to_cancel:
            task.cancel()

        loop.run_until_complete(asyncio.gather(*to_cancel, return_exceptions=True))

        for task in to_cancel:
            if task.cancelled():
                continue
            if task.exception() is not None:
                loop.call_exception_handler({
                    'message': 'unhandled exception during asyncio.run() shutdown',
                    'exception': task.exception(),
                    'task': task,
                })
    except Exception:
        # Ignore errors during cleanup
        pass


def _run_start_batch(
    csv_path: Path,
    run_context: RunContext,
    execute_immediately: bool = True,
) -> Any:
    """Execute the async start_batch helper from synchronous CLI code.
    
    Args:
        csv_path: Validated CSV file path
        run_context: Runtime context for artifacts
        execute_immediately: Whether to execute jobs immediately
        
    Returns:
        Batch manifest object
        
    Raises:
        RuntimeError: If event loop management fails
    """

    async def _invoke():
        return await start_batch(
            str(csv_path),
            run_context,
            execute_immediately=execute_immediately,
        )

    try:
        logger.debug("Starting batch with asyncio.run")
        return asyncio.run(_invoke())
    except RuntimeError as exc:
        if "asyncio.run() cannot be called from a running event loop" in str(exc):
            logger.warning("Active event loop detected, creating new loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_invoke())
            finally:
                try:
                    _cancel_all_tasks(loop)
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.run_until_complete(loop.shutdown_default_executor())
                finally:
                    asyncio.set_event_loop(None)
                    loop.close()
        logger.error("Unexpected RuntimeError during batch start: %s", exc)
        raise


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _iter_jobs(manifest: Any) -> Sequence[Any]:
    jobs = getattr(manifest, "jobs", [])
    if jobs is None:
        return []
    if isinstance(jobs, (list, tuple)):
        return jobs
    return list(jobs)


def _print_job_details(manifest: Any) -> None:
    jobs = _iter_jobs(manifest)
    if not jobs:
        return

    print("\n📋 Job details:")
    for job in jobs:
        # Handle both BatchJob objects and job summary dictionaries
        if isinstance(job, dict):
            status = job.get("status", "unknown")
            job_id = job.get("job_id", "unknown")
            error_message = job.get("error_message") or job.get("error")
        else:
            status = getattr(job, "status", "unknown")
            job_id = getattr(job, "job_id", "unknown")
            error_message = getattr(job, "error_message", None) or getattr(job, "error", None)

        if status == "completed":
            status_icon = "✅"
        elif status == "failed":
            status_icon = "❌"
        else:
            status_icon = "⏳"

        print(f"   {status_icon} {job_id}: {status}")
        if error_message:
            print(f"      Error: {error_message}")


def _print_manifest_overview(manifest: Any, header: str = "✅ Batch status:") -> None:
    print(header)
    print(f"   Batch ID: {getattr(manifest, 'batch_id', 'unknown')}")
    print(f"   Run ID: {getattr(manifest, 'run_id', 'unknown')}")
    print(f"   CSV Path: {getattr(manifest, 'csv_path', 'unknown')}")
    print(f"   Total jobs: {getattr(manifest, 'total_jobs', 0)}")
    print(f"   Completed: {getattr(manifest, 'completed_jobs', 0)}")
    print(f"   Failed: {getattr(manifest, 'failed_jobs', 0)}")
    print(f"   Pending: {getattr(manifest, 'pending_jobs', 0)}")
    created_at = getattr(manifest, 'created_at', '-')
    if created_at:
        print(f"   Created: {created_at}")


def _handle_start_command(args) -> int:
    """Handle batch start command.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("Starting batch execution from %s", args.csv_path)
    print(f"🚀 Starting batch execution from {args.csv_path}")
    execute_immediately = not getattr(args, 'no_execute', False)
    
    try:
        csv_path = _resolve_csv_path(args.csv_path)
    except (FileNotFoundError, ValueError) as error:
        logger.error("CSV validation failed: %s", error)
        print(f"❌ {error}")
        return 1

    run_context = RunContext.get()
    
    try:
        manifest = _run_start_batch(csv_path, run_context, execute_immediately)
    except Exception as error:
        logger.exception("Failed to start batch: %s", error)
        print(f"❌ Failed to start batch: {error}")
        return 1

    print("✅ Batch created successfully!")
    print(f"   Batch ID: {getattr(manifest, 'batch_id', 'unknown')}")
    print(f"   Run ID: {getattr(manifest, 'run_id', 'unknown')}")

    summary = None
    try:
        engine = BatchEngine(run_context)
        summary = engine.get_batch_summary(getattr(manifest, 'batch_id', ''))
    except Exception as error:
        logger.warning("Could not fetch batch summary: %s", error)
        summary = None

    if summary:
        print(f"   Total jobs: {getattr(summary, 'total_jobs', getattr(manifest, 'total_jobs', 0))}")
        print(f"   Completed: {getattr(summary, 'completed_jobs', 0)}")
        print(f"   Failed: {getattr(summary, 'failed_jobs', 0)}")
    else:
        print(f"   Total jobs: {getattr(manifest, 'total_jobs', 0)}")

    print(f"   Jobs directory: {run_context.artifact_dir('jobs')}")
    batch_manifest_dir = Path(run_context.artifact_dir('batch'))
    print(f"   Manifest: {batch_manifest_dir / 'batch_manifest.json'}")

    logger.info("Batch %s created successfully", getattr(manifest, 'batch_id', 'unknown'))
    return 0


def _handle_status_command(args) -> int:
    print(f"📊 Getting status for batch {args.batch_id}")
    run_context = RunContext.get()
    engine = BatchEngine(run_context)

    manifest = engine.get_batch_summary(args.batch_id)
    if manifest is None:
        print(f"❌ Batch {args.batch_id} not found")
        return 1

    _print_manifest_overview(manifest)
    _print_job_details(manifest)
    return 0


def _handle_update_job_command(args) -> int:
    print(f"🔄 Updating job {args.job_id} to {args.status}")
    run_context = RunContext.get()
    engine = BatchEngine(run_context)
    engine.update_job_status(args.job_id, args.status, args.error)
    print("✅ Job status updated successfully!")
    return 0


def _handle_execute_command(args) -> int:
    print(f"🚀 Executing all jobs in batch {args.batch_id}")
    run_context = RunContext.get()
    engine = BatchEngine(run_context)
    result = engine.execute_batch_jobs(args.batch_id)

    print("✅ Batch execution completed!")
    print(f"   Jobs executed: {result.get('executed_jobs', 0)}")
    print(f"   Successful: {result.get('successful_jobs', 0)}")
    print(f"   Failed: {result.get('failed_jobs', 0)}")
    return 0


def create_batch_parser():
    """Create argument parser for batch commands."""
    parser = argparse.ArgumentParser(
        description="bykilt - Browser automation with batch execution support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,  # Disable automatic --help handling
        epilog="""
Examples:
  # Start batch execution from CSV
  python bykilt.py batch start data.csv

  # Get batch status
  python bykilt.py batch status batch_123

  # Update job status
  python bykilt.py batch update-job job_0001 completed

  # Launch web UI (default)
  python bykilt.py ui
        """
    )

    subparsers = parser.add_subparsers(dest='batch_command', help='Batch subcommands', required=True)

    # batch start
    start_parser = subparsers.add_parser('start', help='Start batch execution from CSV')
    start_parser.add_argument('csv_path', help='Path to CSV file')
    start_parser.add_argument('--template', help='Template ID for job configuration')
    start_parser.add_argument('--no-execute', action='store_true', help='Create batch jobs without executing them')

    # batch status
    status_parser = subparsers.add_parser('status', help='Get batch execution status')
    status_parser.add_argument('batch_id', help='Batch ID to check')

    # batch update-job
    update_parser = subparsers.add_parser('update-job', help='Update job status')
    update_parser.add_argument('job_id', help='Job ID to update')
    update_parser.add_argument('status', choices=['completed', 'failed'], help='New status')
    update_parser.add_argument('--error', help='Error message for failed jobs')

    # batch execute
    execute_parser = subparsers.add_parser('execute', help='Execute all jobs in a batch')
    execute_parser.add_argument('batch_id', help='Batch ID to execute')

    return parser


def handle_batch_command(args) -> int:
    """Handle batch-related CLI commands."""
    command = getattr(args, 'batch_command', None)
    try:
        if command == 'start':
            return _handle_start_command(args)
        if command == 'status':
            return _handle_status_command(args)
        if command == 'update-job':
            return _handle_update_job_command(args)
        if command == 'execute':
            return _handle_execute_command(args)
        print(f"❌ Unknown batch command: {command}")
        return 1
    except (FileNotFoundError, PermissionError, ValueError) as error:
        print(f"❌ {error}")
        return 1
    except Exception as exc:  # pragma: no cover - unexpected failure path
        print(f"❌ Error: {exc}")
        import traceback
        traceback.print_exc()
        return 1


def handle_batch_commands():
    """Handle batch commands before Gradio import to avoid argument conflicts."""
    if len(sys.argv) > 1 and sys.argv[1] == 'batch':
        # Special handling for help
        if len(sys.argv) == 2 or (len(sys.argv) > 2 and sys.argv[2] in ['--help', '-h']):
            parser = create_batch_parser()
            parser.print_help()
            sys.exit(0)

        # Handle batch commands using the unified parser
        parser = create_batch_parser()
        try:
            args = parser.parse_args(sys.argv[2:])  # Skip 'bykilt.py batch' part
            exit_code = handle_batch_command(args)
            sys.exit(exit_code)
        except SystemExit as e:
            # argparse prints help and exits, return the exit code
            sys.exit(e.code if hasattr(e, 'code') else 1)
