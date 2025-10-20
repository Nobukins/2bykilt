#!/usr/bin/env python3
"""
Performance Benchmark for Sandbox Implementation

Measures the performance overhead of sandbox execution compared to native execution.

Usage:
    python scripts/benchmark_sandbox_performance.py [--iterations N] [--output FILE]
"""

import argparse
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from security.sandbox_manager import SandboxManager, SandboxConfig
import subprocess


class SandboxBenchmark:
    """Benchmark sandbox performance"""
    
    def __init__(self, iterations: int = 10):
        self.iterations = iterations
        self.results: Dict[str, Dict[str, List[float]]] = {}
        
    def measure_native(self, command: List[str]) -> float:
        """Measure native execution time"""
        start = time.time()
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        elapsed = time.time() - start
        return elapsed
    
    def measure_sandbox(self, command: List[str], config: SandboxConfig, workspace: str) -> float:
        """Measure sandboxed execution time"""
        manager = SandboxManager(config, workspace)
        start = time.time()
        result = manager.execute(command)
        elapsed = time.time() - start
        return elapsed
    
    def benchmark_command(
        self,
        name: str,
        command: List[str],
        description: str = ""
    ):
        """Benchmark a specific command"""
        print(f"\n{'='*60}")
        print(f"Benchmark: {name}")
        if description:
            print(f"Description: {description}")
        print(f"Command: {' '.join(command)}")
        print(f"Iterations: {self.iterations}")
        print('='*60)
        
        native_times: List[float] = []
        sandbox_times: List[float] = []
        
        config = SandboxConfig(
            enabled=True,
            mode="enforce",
            timeout_seconds=30,
            cpu_time_limit=10,
            memory_limit_mb=512
        )
        
        with tempfile.TemporaryDirectory() as workspace:
            # Warmup
            print("Warming up...", end=" ", flush=True)
            try:
                self.measure_native(command)
                self.measure_sandbox(command, config, workspace)
            except Exception as e:
                print(f"⚠️  Warmup failed: {e}")
                return
            print("Done")
            
            # Measure native execution
            print(f"Measuring native execution...", end=" ", flush=True)
            for i in range(self.iterations):
                try:
                    elapsed = self.measure_native(command)
                    native_times.append(elapsed)
                    print(f"{i+1}", end=" ", flush=True)
                except Exception as e:
                    print(f"\n⚠️  Native execution {i+1} failed: {e}")
            print("Done")
            
            # Measure sandboxed execution
            print(f"Measuring sandboxed execution...", end=" ", flush=True)
            for i in range(self.iterations):
                try:
                    elapsed = self.measure_sandbox(command, config, workspace)
                    sandbox_times.append(elapsed)
                    print(f"{i+1}", end=" ", flush=True)
                except Exception as e:
                    print(f"\n⚠️  Sandbox execution {i+1} failed: {e}")
            print("Done")
        
        if not native_times or not sandbox_times:
            print("⚠️  Insufficient data for analysis")
            return
        
        # Calculate statistics
        native_mean = statistics.mean(native_times)
        native_stdev = statistics.stdev(native_times) if len(native_times) > 1 else 0
        
        sandbox_mean = statistics.mean(sandbox_times)
        sandbox_stdev = statistics.stdev(sandbox_times) if len(sandbox_times) > 1 else 0
        
        overhead_abs = sandbox_mean - native_mean
        overhead_pct = (overhead_abs / native_mean) * 100 if native_mean > 0 else 0
        
        # Store results
        self.results[name] = {
            "native": native_times,
            "sandbox": sandbox_times,
            "native_mean": native_mean,
            "native_stdev": native_stdev,
            "sandbox_mean": sandbox_mean,
            "sandbox_stdev": sandbox_stdev,
            "overhead_abs": overhead_abs,
            "overhead_pct": overhead_pct
        }
        
        # Print results
        print(f"\n{'='*60}")
        print("Results:")
        print(f"  Native:   {native_mean*1000:6.2f}ms ± {native_stdev*1000:5.2f}ms")
        print(f"  Sandbox:  {sandbox_mean*1000:6.2f}ms ± {sandbox_stdev*1000:5.2f}ms")
        print(f"  Overhead: {overhead_abs*1000:6.2f}ms ({overhead_pct:+.1f}%)")
        print('='*60)
    
    def run_benchmarks(self):
        """Run all benchmarks"""
        print(f"\n{'#'*60}")
        print(f"# Sandbox Performance Benchmark")
        print(f"# Iterations per test: {self.iterations}")
        print(f"{'#'*60}\n")
        
        # Benchmark 1: Simple echo
        self.benchmark_command(
            "echo",
            ["echo", "Hello World"],
            "Minimal command to measure base overhead"
        )
        
        # Benchmark 2: Python hello world
        self.benchmark_command(
            "python_hello",
            ["python", "-c", "print('Hello World')"],
            "Simple Python execution"
        )
        
        # Benchmark 3: Python with imports
        self.benchmark_command(
            "python_imports",
            ["python", "-c", "import sys, os, json; print('Loaded')"],
            "Python with module imports"
        )
        
        # Benchmark 4: Filesystem operations
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            self.benchmark_command(
                "filesystem_ops",
                ["bash", "-c", f"echo 'test' > {test_file} && cat {test_file}"],
                "Basic filesystem read/write"
            )
        
        # Benchmark 5: CPU-bound task
        self.benchmark_command(
            "cpu_bound",
            ["python", "-c", "x = sum(range(100000))"],
            "CPU-intensive computation"
        )
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print benchmark summary"""
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print('='*60)
        print(f"{'Test':<20} {'Native':>10} {'Sandbox':>10} {'Overhead':>10}")
        print('-'*60)
        
        for name, data in self.results.items():
            native_ms = data['native_mean'] * 1000
            sandbox_ms = data['sandbox_mean'] * 1000
            overhead_pct = data['overhead_pct']
            
            print(f"{name:<20} {native_ms:>9.2f}ms {sandbox_ms:>9.2f}ms {overhead_pct:>8.1f}%")
        
        print('='*60)
        
        # Overall statistics
        all_overheads = [d['overhead_pct'] for d in self.results.values()]
        if all_overheads:
            avg_overhead = statistics.mean(all_overheads)
            min_overhead = min(all_overheads)
            max_overhead = max(all_overheads)
            
            print(f"\nOverall Overhead Statistics:")
            print(f"  Average: {avg_overhead:+.1f}%")
            print(f"  Minimum: {min_overhead:+.1f}%")
            print(f"  Maximum: {max_overhead:+.1f}%")
        
        print('='*60)
        
        # Interpretation
        print("\nInterpretation:")
        if all_overheads:
            if avg_overhead < 10:
                print("  ✅ Excellent: Overhead is minimal (<10%)")
            elif avg_overhead < 25:
                print("  ✅ Good: Overhead is acceptable (10-25%)")
            elif avg_overhead < 50:
                print("  ⚠️  Moderate: Overhead is noticeable (25-50%)")
            else:
                print("  ⚠️  High: Overhead is significant (>50%)")
                print("     Note: Short-running commands have higher relative overhead")
    
    def save_results(self, output_file: str):
        """Save results to JSON file"""
        import json
        
        output_data = {
            "iterations": self.iterations,
            "results": {}
        }
        
        for name, data in self.results.items():
            output_data["results"][name] = {
                "native_mean_ms": data["native_mean"] * 1000,
                "native_stdev_ms": data["native_stdev"] * 1000,
                "sandbox_mean_ms": data["sandbox_mean"] * 1000,
                "sandbox_stdev_ms": data["sandbox_stdev"] * 1000,
                "overhead_ms": data["overhead_abs"] * 1000,
                "overhead_pct": data["overhead_pct"]
            }
        
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark sandbox performance overhead"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations per test (default: 10)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file for results"
    )
    
    args = parser.parse_args()
    
    benchmark = SandboxBenchmark(iterations=args.iterations)
    benchmark.run_benchmarks()
    
    if args.output:
        benchmark.save_results(args.output)


if __name__ == "__main__":
    main()
