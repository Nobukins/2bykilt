"""Batch command CLI interface for bykilt.

This module handles batch execution commands through the CLI.
"""
import argparse
import os
import sys
import asyncio


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


def handle_batch_command(args):
    """Handle batch-related CLI commands."""
    try:
        from src.batch.engine import BatchEngine, start_batch
        from src.runtime.run_context import RunContext

        if hasattr(args, 'batch_command') and args.batch_command == 'start':
            print(f"🚀 Starting batch execution from {args.csv_path}")

            # Determine execution mode
            execute_immediately = not getattr(args, 'no_execute', False)

            # Create run context
            run_context = RunContext.get()

            # Start batch
            manifest = start_batch(args.csv_path, run_context, execute_immediately=execute_immediately)
            # If start_batch returned a coroutine (async implementation), run it to completion.
            if asyncio.iscoroutine(manifest):
                manifest = asyncio.run(manifest)

            print("✅ Batch created successfully!")
            print(f"   Batch ID: {manifest.batch_id}")
            print(f"   Run ID: {manifest.run_id}")
            # If jobs were executed immediately, try to reload the manifest/summary
            # so we can display updated completed/failed counts.
            try:
                engine = BatchEngine(run_context)
                summary = engine.get_batch_summary(manifest.batch_id)
                if summary:
                    print(f"   Total jobs: {summary.total_jobs}")
                    print(f"   Completed: {summary.completed_jobs}")
                    print(f"   Failed: {summary.failed_jobs}")
                else:
                    print(f"   Total jobs: {manifest.total_jobs}")
            except Exception:
                print(f"   Total jobs: {manifest.total_jobs}")
            print(f"   Jobs directory: {run_context.artifact_dir('jobs')}")
            print(f"   Manifest: {os.path.join(run_context.artifact_dir('batch'), 'batch_manifest.json')}")

            return 0

        elif hasattr(args, 'batch_command') and args.batch_command == 'status':
            print(f"📊 Getting status for batch {args.batch_id}")

            # Create run context and engine
            run_context = RunContext.get()
            engine = BatchEngine(run_context)

            # Get batch status
            manifest = engine.get_batch_summary(args.batch_id)

            if manifest is None:
                print(f"❌ Batch {args.batch_id} not found")
                return 1

            print("✅ Batch status:")
            print(f"   Batch ID: {manifest.batch_id}")
            print(f"   Run ID: {manifest.run_id}")
            print(f"   CSV Path: {manifest.csv_path}")
            print(f"   Total jobs: {manifest.total_jobs}")
            print(f"   Completed: {manifest.completed_jobs}")
            print(f"   Failed: {manifest.failed_jobs}")
            print(f"   Created: {manifest.created_at}")

            print("\n📋 Job details:")
            for job in manifest.jobs:
                status_icon = "✅" if job['status'] == "completed" else "❌" if job['status'] == "failed" else "⏳"
                print(f"   {status_icon} {job['job_id']}: {job['status']}")
                if job.get('error_message'):
                    print(f"      Error: {job['error_message']}")

            return 0

        elif hasattr(args, 'batch_command') and args.batch_command == 'update-job':
            print(f"🔄 Updating job {args.job_id} to {args.status}")

            # Create run context and engine
            run_context = RunContext.get()
            engine = BatchEngine(run_context)

            # Update job status
            engine.update_job_status(args.job_id, args.status, args.error)

            print("✅ Job status updated successfully!")
            return 0

        elif hasattr(args, 'batch_command') and args.batch_command == 'execute':
            print(f"🚀 Executing all jobs in batch {args.batch_id}")

            # Create run context and engine
            run_context = RunContext.get()
            engine = BatchEngine(run_context)

            # Execute batch jobs
            result = engine.execute_batch_jobs(args.batch_id)

            print("✅ Batch execution completed!")
            print(f"   Jobs executed: {result.get('executed_jobs', 0)}")
            print(f"   Successful: {result.get('successful_jobs', 0)}")
            print(f"   Failed: {result.get('failed_jobs', 0)}")
            return 0

    except Exception as e:
        print(f"❌ Error: {e}")
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
