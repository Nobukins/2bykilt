#!/usr/bin/env python3
"""
Example usage of the metrics foundation system.

This script demonstrates how to use the metrics collection system
integrated with batch processing in 2bykilt.
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def example_basic_metrics():
    """Example of basic metrics collection."""
    print("📊 Basic Metrics Collection Example")
    print("=" * 50)

    from src.metrics import get_metrics_collector, MetricType

    collector = get_metrics_collector()

    # Record some basic metrics
    collector.record_metric("user_logins", 1, metric_type=MetricType.COUNTER, tags={"user_type": "admin"})
    collector.record_metric("response_time", 0.245, metric_type=MetricType.HISTOGRAM, tags={"endpoint": "/api/users"})
    collector.record_metric("memory_usage", 85.5, metric_type=MetricType.GAUGE, tags={"service": "web"})
    collector.record_metric("cpu_usage", 12.3, metric_type=MetricType.GAUGE, tags={"service": "web"})

    print("✅ Recorded basic metrics")

def example_batch_processing():
    """Example of batch processing with metrics."""
    print("\n🔄 Batch Processing with Metrics Example")
    print("=" * 50)

    from src.runtime.run_context import RunContext
    from src.batch.engine import BatchEngine

    # Create run context
    run_context = RunContext.get()
    print(f"📋 Run context: {run_context.run_id_base}")

    # Create batch engine
    engine = BatchEngine(run_context)

    # Create sample CSV data
    csv_content = """task_id,name,priority,status
1,Process user data,high,pending
2,Generate report,medium,pending
3,Send notifications,low,pending
4,Update database,high,pending"""

    # Create temporary CSV file
    csv_path = Path("sample_batch.csv")
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write(csv_content)

    try:
        # Create batch
        manifest = engine.create_batch_jobs(str(csv_path))
        print(f"✅ Created batch: {manifest.batch_id}")
        print(f"   Total jobs: {manifest.total_jobs}")

        # Simulate job processing
        for i, job in enumerate(manifest.jobs):
            print(f"   Processing job {job.job_id}...")

            # Simulate some processing time
            time.sleep(0.1)

            # Mark job as completed (or failed for demo)
            if i < len(manifest.jobs) - 1:  # Complete all but last job
                engine.update_job_status(job.job_id, "completed")
                print(f"   ✅ Job {job.job_id} completed")
            else:
                engine.update_job_status(job.job_id, "failed", "Simulated error")
                print(f"   ❌ Job {job.job_id} failed")

    finally:
        # Clean up
        if csv_path.exists():
            csv_path.unlink()

def example_metrics_export():
    """Example of metrics data export."""
    print("\n💾 Metrics Export Example")
    print("=" * 50)

    from src.metrics import get_metrics_collector

    collector = get_metrics_collector()

    # Export to JSON
    json_data = collector.export_to_json()
    print("📄 JSON Export (first 200 chars):")
    print(json_data[:200] + "..." if len(json_data) > 200 else json_data)
    print()

    # Export to CSV files (to artifacts/metrics directory)
    csv_files = collector.export_to_csv("artifacts/metrics")
    print(f"📊 Exported {len(csv_files)} CSV files to artifacts/metrics/:")
    for csv_file in csv_files:
        print(f"   - {Path(csv_file).name}")

def example_decorators():
    """Example of using metrics decorators."""
    print("\n🎯 Metrics Decorators Example")
    print("=" * 50)

    from src.metrics import record_execution_time, record_memory_usage

    @record_execution_time
    def sample_function():
        """A sample function to demonstrate execution time tracking."""
        time.sleep(0.2)
        return "Function completed"

    @record_memory_usage
    def memory_intensive_function():
        """A sample function to demonstrate memory usage tracking."""
        data = [i for i in range(10000)]  # Create some data
        result = sum(data)
        return result

    print("⏱️  Running function with execution time tracking...")
    result1 = sample_function()
    print(f"   Result: {result1}")

    print("💾 Running function with memory usage tracking...")
    result2 = memory_intensive_function()
    print(f"   Result: {result2}")

def main():
    """Run all examples."""
    print("🚀 2Bykilt Metrics Foundation - Usage Examples")
    print("=" * 60)

    try:
        # Initialize metrics system
        from src.metrics import initialize_metrics
        initialize_metrics()
        print("✅ Metrics system initialized")

        # Run examples
        example_basic_metrics()
        example_batch_processing()
        example_decorators()
        example_metrics_export()

        print("\n🎉 All examples completed successfully!")
        print("\n💡 Key Features Demonstrated:")
        print("   • Basic metrics collection (counters, gauges, histograms)")
        print("   • Batch processing with automatic metrics recording")
        print("   • Function decorators for execution time and memory tracking")
        print("   • Data export to JSON and CSV formats")
        print("   • Integration with existing 2bykilt systems")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
