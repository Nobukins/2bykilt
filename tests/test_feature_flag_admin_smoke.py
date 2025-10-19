#!/usr/bin/env python3
"""Simple smoke test for Feature Flag Admin UI (Issue #272)

This script performs basic validation of the new admin panel:
1. Imports all required modules
2. Creates the admin panel component
3. Verifies FeatureFlags API methods work correctly
"""
import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.ci_safe
def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    try:
        from src.config.feature_flags import FeatureFlags
        from src.ui.admin.feature_flag_panel import create_feature_flag_admin_panel
        import gradio as gr
        print("✅ All imports successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        assert False, f"Import failed: {e}"


@pytest.mark.ci_safe
def test_feature_flags_api():
    """Test FeatureFlags class API methods."""
    print("\n🔍 Testing FeatureFlags API...")
    try:
        from src.config.feature_flags import FeatureFlags
        
        # Test get_all_flags()
        all_flags = FeatureFlags.get_all_flags()
        if not all_flags:
            print("⚠️  No flags loaded (this is okay if config file is missing)")
        else:
            print(f"✅ get_all_flags() returned {len(all_flags)} flags")
            
            # Show a sample flag
            sample_name = list(all_flags.keys())[0]
            sample_data = all_flags[sample_name]
            print(f"   Sample flag: {sample_name}")
            print(f"   - value: {sample_data.get('value')}")
            print(f"   - type: {sample_data.get('type')}")
            print(f"   - source: {sample_data.get('source')}")
        
        # Test get_flag_metadata()
        if all_flags:
            test_flag_name = list(all_flags.keys())[0]
            metadata = FeatureFlags.get_flag_metadata(test_flag_name)
            if metadata:
                print(f"✅ get_flag_metadata('{test_flag_name}') returned valid data")
            else:
                print(f"❌ get_flag_metadata('{test_flag_name}') returned None")
                assert False, f"get_flag_metadata('{test_flag_name}') returned None"
        
        # Test with non-existent flag
        nonexistent = FeatureFlags.get_flag_metadata("nonexistent_flag_xyz")
        if nonexistent is None:
            print("✅ get_flag_metadata() correctly returns None for non-existent flag")
        else:
            print("❌ get_flag_metadata() should return None for non-existent flag")
            assert False, "get_flag_metadata() should return None for non-existent flag"
        
        return True
        
    except Exception as e:
        print(f"❌ FeatureFlags API test failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"FeatureFlags API test failed: {e}"


@pytest.mark.ci_safe
def test_panel_creation():
    """Test admin panel creation without launching UI."""
    print("\n🔍 Testing admin panel creation...")
    try:
        from src.ui.admin.feature_flag_panel import create_feature_flag_admin_panel
        import gradio as gr
        
        # Create panel (this will construct the Gradio Blocks)
        panel = create_feature_flag_admin_panel()
        
        if isinstance(panel, gr.Blocks):
            print("✅ Admin panel created successfully (gr.Blocks instance)")
            return True
        else:
            print(f"❌ Panel creation returned unexpected type: {type(panel)}")
            assert False, f"Panel creation returned unexpected type: {type(panel)}"
            
    except Exception as e:
        print(f"❌ Panel creation failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Panel creation failed: {e}"


def main():
    """Run all tests."""
    print("=" * 60)
    print("Feature Flag Admin UI - Smoke Test")
    print("Issue #272")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    
    if results[0][1]:  # Only continue if imports work
        results.append(("FeatureFlags API", test_feature_flags_api()))
        results.append(("Panel Creation", test_panel_creation()))
    else:
        print("\n⚠️  Skipping remaining tests due to import failure")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
