#!/usr/bin/env python3
"""
Test script for metrics foundation integration.

This script tests the metrics collection functionality integrated with
the batch processing system.
"""

import sys
import pytest
import os
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

@pytest.mark.ci_safe
def test_metrics_initialization():
    """Test metrics system initialization."""
    print("🧪 Testing metrics system initialization...")

    try:
        from src.metrics import initialize_metrics, get_metrics_collector

        # Initialize metrics
        initialize_metrics()
        print("✅ Metrics system initialized successfully")

        # Get collector
        collector = get_metrics_collector()
        if collector is not None:
            print("✅ Metrics collector retrieved successfully")
        else:
            print("❌ Failed to get metrics collector")
            assert False, "Failed to get metrics collector"

        return True

    except Exception as e:
        print(f"❌ Metrics initialization failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Metrics initialization failed: {e}"

@pytest.mark.ci_safe
def test_batch_metrics_integration():
    """Test batch processing with metrics collection."""
    print("\n🧪 Testing batch processing with metrics integration...")

    try:
        from src.runtime.run_context import RunContext
        from src.batch.engine import BatchEngine

        # Create run context
        run_context = RunContext.get()
        print(f"📋 Run context created: {run_context.run_id_base}")

        # Create batch engine
        engine = BatchEngine(run_context)

        # Create a simple test CSV content
        test_csv_content = """name,value,status
Test Job 1,100,pending
Test Job 2,200,pending
Test Job 3,300,pending"""

        # Create temporary CSV file
        test_csv_path = Path("test_batch.csv")
        with open(test_csv_path, 'w', encoding='utf-8') as f:
            f.write(test_csv_content)

        try:
            # Create batch
            manifest = engine.create_batch_jobs(str(test_csv_path))
            print(f"✅ Batch created: {manifest.batch_id} with {manifest.total_jobs} jobs")

            # Simulate job completion
            for job in manifest.jobs[:2]:  # Complete first 2 jobs
                engine.update_job_status(job.job_id, "completed")
                print(f"✅ Job {job.job_id} marked as completed")

            # Simulate job failure
            if len(manifest.jobs) > 2:
                engine.update_job_status(manifest.jobs[2].job_id, "failed", "Test error")
                print(f"✅ Job {manifest.jobs[2].job_id} marked as failed")

            return True

        finally:
            # Clean up test file
            if test_csv_path.exists():
                test_csv_path.unlink()

    except Exception as e:
        print(f"❌ Batch metrics integration test failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Batch metrics integration test failed: {e}"

@pytest.mark.ci_safe
def test_metrics_export():
    """Test metrics data export."""
    print("\n🧪 Testing metrics data export...")

    try:
        from src.metrics import get_metrics_collector

        collector = get_metrics_collector()
        if collector is None:
            print("❌ No metrics collector available")
            assert False, "No metrics collector available"

        # Export metrics to JSON
        json_data = collector.export_to_json()
        if json_data:
            print("✅ Metrics exported to JSON successfully")
            print(f"📊 JSON data length: {len(json_data)} characters")
        else:
            print("❌ Failed to export metrics to JSON")
            assert False, "Failed to export metrics to JSON"

        # Export metrics to CSV
        csv_data = collector.export_to_csv()
        if csv_data:
            print("✅ Metrics exported to CSV successfully")
            print(f"📊 CSV data length: {len(csv_data)} characters")
        else:
            print("❌ Failed to export metrics to CSV")
            assert False, "Failed to export metrics to CSV"

        return True

    except Exception as e:
        print(f"❌ Metrics export test failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Metrics export test failed: {e}"

def main():
    """Run all tests."""
    print("🚀 Starting metrics foundation integration tests...\n")

    tests = [
        test_metrics_initialization,
        test_batch_metrics_integration,
        test_metrics_export
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Metrics foundation integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
