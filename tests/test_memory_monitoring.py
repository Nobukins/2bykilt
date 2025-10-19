#!/usr/bin/env python3
"""
Memory monitoring test script for git-script Edge crash issue
"""

import sys
import pytest
import os
sys.path.append('/Users/nobuaki/Documents/Github/copilot-ports/magic-trainings/2bykilt')

from src.utils.memory_monitor import memory_monitor
from src.utils.app_logger import logger

@pytest.mark.local_only
def test_memory_monitoring():
    """Test memory monitoring functionality"""
    
    print("🧠 Memory Monitoring Test")
    print("=" * 50)
    
    # Test memory status
    status = memory_monitor.get_memory_status()
    print(f"📊 Memory Status:")
    print(f"   Total: {status['total_mb']}MB")
    print(f"   Available: {status['available_mb']}MB")
    print(f"   Used: {status['used_percent']:.1f}%")
    print(f"   Pressure Level: {status['pressure_level']}")
    print(f"   Low Memory: {status['is_low_memory']}")
    print()
    
    # Test browser safety check
    browsers_to_test = ['chrome', 'edge', 'chromium']
    
    for browser in browsers_to_test:
        is_safe, msg = memory_monitor.is_safe_for_browser(browser)
        status_emoji = "✅" if is_safe else "⚠️"
        print(f"{status_emoji} {browser.upper()}: {msg}")
        
        if not is_safe:
            fallback = memory_monitor.suggest_fallback_browser(browser)
            print(f"   🔄 Suggested fallback: {fallback}")
    
    print()
    
    # Test optimized arguments
    for browser in browsers_to_test:
        args = memory_monitor.get_optimized_browser_args(browser)
        print(f"🔧 {browser.upper()} optimized args ({len(args)} total):")
        for i, arg in enumerate(args[:5]):  # Show first 5 args
            print(f"   {i+1}. {arg}")
        if len(args) > 5:
            print(f"   ... and {len(args) - 5} more")
        print()

def simulate_memory_pressure():
    """Simulate different memory pressure scenarios"""
    
    print("🧪 Memory Pressure Simulation")
    print("=" * 50)
    
    # Test different memory scenarios
    test_scenarios = [
        ("Low pressure", 30.0),
        ("Medium pressure", 65.0),
        ("High pressure", 85.0),
        ("Critical pressure", 97.0)
    ]
    
    original_threshold = memory_monitor.memory_pressure_threshold
    
    for scenario_name, pressure_percent in test_scenarios:
        print(f"\n📊 Scenario: {scenario_name} ({pressure_percent}%)")
        
        # Temporarily modify pressure calculation for testing
        memory_monitor.memory_pressure_threshold = pressure_percent - 10
        
        # Check Edge safety with simulated pressure
        is_safe, msg = memory_monitor.is_safe_for_browser('edge')
        fallback = memory_monitor.suggest_fallback_browser('edge')
        
        status_emoji = "✅" if is_safe else "⚠️"
        print(f"   {status_emoji} Edge safety: {msg}")
        print(f"   🔄 Suggested: edge → {fallback}")
    
    # Restore original threshold
    memory_monitor.memory_pressure_threshold = original_threshold

if __name__ == "__main__":
    try:
        test_memory_monitoring()
        simulate_memory_pressure()
        
        print("\n🎉 Memory monitoring test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
