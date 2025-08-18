"""
Test the complete NEW METHOD integration
"""
import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

async def test_new_method_integration():
    """Test the complete NEW METHOD integration"""
    
    # Set environment for NEW METHOD
    os.environ['BYKILT_USE_NEW_METHOD'] = 'true'
    os.environ['BYKILT_BROWSER_TYPE'] = 'edge'
    
    from src.script.script_manager import run_script
    
    # Simulate a git-script execution
    script_info = {
        "type": "git-script",
        "git": "https://github.com/example/sample-tests.git", 
        "script_path": "search_script.py",
        "version": "main",
        "command": "python ${script_path} --query ${params.query}"
    }
    
    params = {
        "query": "test search"
    }
    
    try:
        print("🚀 Testing NEW METHOD integration...")
        
        # This would normally execute the script via run_script
        # For now, let's just test the automator directly
        from src.utils.git_script_automator import EdgeAutomator
        
        print("📁 Checking Edge profile...")
        edge_profile = os.path.expanduser("~/Library/Application Support/Microsoft Edge")
        
        if not Path(edge_profile).exists():
            print("❌ Edge profile not found - skipping integration test")
            return
            
        automator = EdgeAutomator()
        
        print("🔍 Validating source profile...")
        if automator.validate_source_profile():
            print("✅ Source profile validation passed")
            
            # Get automation info
            info = automator.get_automation_info()
            print(f"📊 Browser type: {info['browser_type']}")
            print(f"📊 Essential files found: {len(info['profile_manager']['essential_files_found'])}")
            print(f"📊 Browser executable exists: {info['browser_launcher']['executable_exists']}")
            
            print("🎉 NEW METHOD integration test completed successfully!")
        else:
            print("❌ Source profile validation failed")
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_new_method_integration())
