#!/usr/bin/env python3
"""
Measure and record security scan performance metrics.

This script measures the execution time of security scanning tools and
records the results for performance analysis and optimization.

Usage:
    python scripts/measure_scan_perf.py --tool <tool_name> --command <command> --output <output_file>
"""

import subprocess
import time
import json
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


def run_command_with_timing(command: str) -> Dict[str, Any]:
    """Run a command and measure its execution time."""
    start_time = time.time()
    start_datetime = datetime.now(timezone.utc)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        end_time = time.time()
        end_datetime = datetime.now(timezone.utc)

        return {
            'success': result.returncode == 0,
            'return_code': result.returncode,
            'execution_time_seconds': end_time - start_time,
            'start_time': start_datetime.isoformat(),
            'end_time': end_datetime.isoformat(),
            'stdout': result.stdout,
            'stderr': result.stderr,
            'command': command
        }

    except subprocess.TimeoutExpired:
        end_time = time.time()
        return {
            'success': False,
            'return_code': -1,
            'execution_time_seconds': end_time - start_time,
            'start_time': start_datetime.isoformat(),
            'end_time': datetime.now(timezone.utc).isoformat(),
            'stdout': '',
            'stderr': 'Command timed out after 3600 seconds',
            'command': command
        }

    except Exception as e:
        end_time = time.time()
        return {
            'success': False,
            'return_code': -1,
            'execution_time_seconds': end_time - start_time,
            'start_time': start_datetime.isoformat(),
            'end_time': datetime.now(timezone.utc).isoformat(),
            'stdout': '',
            'stderr': str(e),
            'command': command
        }


def load_existing_metrics(output_file: Path) -> Dict[str, Any]:
    """Load existing performance metrics if file exists."""
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            # If file exists but is corrupted, start fresh
            pass

    # Return default structure
    return {
        'metadata': {
            'tool': 'scan_performance_measure',
            'version': '1.0.0',
            'created_at': datetime.now(timezone.utc).isoformat()
        },
        'measurements': []
    }


def save_metrics(metrics: Dict[str, Any], output_file: Path):
    """Save performance metrics to file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description='Measure security scan performance'
    )
    parser.add_argument(
        '--tool',
        required=True,
        help='Name of the security tool being measured'
    )
    parser.add_argument(
        '--command',
        required=True,
        help='Command to execute for measurement'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output file path for performance metrics'
    )
    parser.add_argument(
        '--baseline',
        action='store_true',
        help='Mark this measurement as a baseline'
    )

    args = parser.parse_args()

    output_path = Path(args.output)

    # Load existing metrics
    metrics = load_existing_metrics(output_path)

    # Run command and measure performance
    print(f"Running command: {args.command}")
    result = run_command_with_timing(args.command)

    # Add measurement to metrics
    measurement = {
        'tool': args.tool,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'baseline': args.baseline,
        'performance': {
            'execution_time_seconds': result['execution_time_seconds'],
            'success': result['success'],
            'return_code': result['return_code']
        },
        'command': result['command']
    }

    metrics['measurements'].append(measurement)

    # Update metadata
    metrics['metadata']['last_updated'] = datetime.now(timezone.utc).isoformat()
    metrics['metadata']['total_measurements'] = len(metrics['measurements'])

    # Save metrics
    save_metrics(metrics, output_path)

    # Print results
    print(f"Measurement completed in {result['execution_time_seconds']:.2f} seconds")
    print(f"Success: {result['success']}")
    print(f"Results saved to {output_path}")

    # Exit with the same code as the measured command
    sys.exit(result['return_code'])


if __name__ == '__main__':
    main()
