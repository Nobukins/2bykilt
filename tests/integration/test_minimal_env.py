"""
Integration Tests for Minimal Environment (Issue #43)

Tests that the application can run with requirements-minimal.txt only,
ensuring zero LLM dependencies when ENABLE_LLM=false.

Run with:
    ENABLE_LLM=false pytest tests/integration/test_minimal_env.py -v
"""

import os
import sys
import pytest
from pathlib import Path

# Ensure ENABLE_LLM is false for these tests
@pytest.fixture(scope="module", autouse=True)
def enforce_minimal_mode():
    """Ensure tests run in minimal mode"""
    enable_llm = os.getenv("ENABLE_LLM", "").lower()
    if enable_llm == "true":
        pytest.skip("These tests require ENABLE_LLM=false (minimal mode)")
    # If ENABLE_LLM is not set or is false, tests will run
    yield


@pytest.mark.ci_safe
class TestMinimalEnvironmentImports:
    """Test core modules can be imported in minimal mode"""
    
    def test_feature_flags_import(self):
        """Feature flags module should load"""
        from src.config.feature_flags import is_llm_enabled
        assert is_llm_enabled() is False
        
    def test_config_adapter_import(self):
        """Config adapter should load and provide safe defaults"""
        from src.config.config_adapter import config_adapter
        cfg = config_adapter.get_effective_config()
        
        assert cfg is not None
        assert isinstance(cfg, dict)
        # LLM settings should have safe defaults
        assert cfg.get("llm_provider") in ("disabled", "openai")  # openai might be default
        
    def test_utils_import(self):
        """Utils module should load with LLM features disabled"""
        from src.utils.utils import is_llm_available
        assert is_llm_available() is False
        
    def test_batch_engine_import(self):
        """Batch engine should load (non-LLM feature)"""
        from src.batch.engine import BatchEngine
        assert BatchEngine is not None
        
    def test_screenshot_manager_import(self):
        """Screenshot manager should load (non-LLM feature)"""
        from src.core.screenshot_manager import capture_page_screenshot
        assert capture_page_screenshot is not None


@pytest.mark.ci_safe
class TestMinimalEnvironmentLLMBlocking:
    """Test LLM modules are properly blocked"""
    
    def test_llm_utils_blocked(self):
        """LLM utils should raise ImportError"""
        with pytest.raises(ImportError, match="LLM functionality is disabled"):
            from src.utils import llm
            
    def test_agent_blocked(self):
        """Agent module should raise ImportError"""
        with pytest.raises(ImportError, match="disabled.*ENABLE_LLM"):
            from src.agent import custom_agent
            
    def test_custom_controller_blocked(self):
        """Custom controller should raise ImportError"""
        with pytest.raises(ImportError, match="disabled.*ENABLE_LLM"):
            from src.controller import custom_controller
            
    def test_custom_browser_blocked(self):
        """Custom browser should raise ImportError"""
        with pytest.raises(ImportError, match="disabled.*ENABLE_LLM"):
            from src.browser import custom_browser
            
    def test_docker_sandbox_blocked(self):
        """Docker sandbox should raise ImportError"""
        with pytest.raises(ImportError, match="disabled.*ENABLE_LLM"):
            from src.llm import docker_sandbox


@pytest.mark.ci_safe
class TestMinimalEnvironmentNoForbiddenPackages:
    """Test no forbidden LLM packages are loaded"""
    
    FORBIDDEN_PACKAGES = {
        "langchain",
        "langchain_core",
        "langchain_openai",
        "langchain_anthropic",
        "openai",
        "anthropic",
        "browser_use",
        "mem0",
        "faiss",
    }
    
    def test_no_langchain_in_modules(self):
        """No langchain packages should be in sys.modules"""
        langchain_modules = [
            m for m in sys.modules
            if m.startswith("langchain")
        ]
        assert len(langchain_modules) == 0, (
            f"Found langchain modules: {langchain_modules}"
        )
        
    def test_no_openai_in_modules(self):
        """No openai package should be in sys.modules"""
        openai_modules = [
            m for m in sys.modules
            if m == "openai" or m.startswith("openai.")
        ]
        assert len(openai_modules) == 0, (
            f"Found openai modules: {openai_modules}"
        )
        
    def test_no_anthropic_in_modules(self):
        """No anthropic package should be in sys.modules"""
        anthropic_modules = [
            m for m in sys.modules
            if m == "anthropic" or m.startswith("anthropic.")
        ]
        assert len(anthropic_modules) == 0, (
            f"Found anthropic modules: {anthropic_modules}"
        )
        
    def test_no_browser_use_in_modules(self):
        """No browser_use package should be in sys.modules"""
        browser_use_modules = [
            m for m in sys.modules
            if m == "browser_use" or m.startswith("browser_use.")
        ]
        assert len(browser_use_modules) == 0, (
            f"Found browser_use modules: {browser_use_modules}"
        )
        
    def test_no_forbidden_packages_in_modules(self):
        """Comprehensive check: no forbidden packages in sys.modules"""
        found_forbidden = []
        for module_name in sys.modules:
            for forbidden in self.FORBIDDEN_PACKAGES:
                if module_name == forbidden or module_name.startswith(f"{forbidden}."):
                    found_forbidden.append(module_name)
                    
        assert len(found_forbidden) == 0, (
            f"Found {len(found_forbidden)} forbidden packages: {found_forbidden[:10]}"
        )


@pytest.mark.ci_safe
class TestMinimalEnvironmentHelperFunctions:
    """Test helper functions work correctly in minimal mode"""
    
    def test_is_llm_available_returns_false(self):
        """is_llm_available() should return False"""
        from src.utils.utils import is_llm_available
        assert is_llm_available() is False
        
    def test_require_llm_decorator_blocks(self):
        """@require_llm decorator should raise error"""
        from src.utils.utils import require_llm
        import gradio as gr
        
        @require_llm
        def dummy_llm_function():
            return "should not reach here"
            
        with pytest.raises(gr.Error, match="LLM functionality is disabled"):
            dummy_llm_function()
            
    def test_config_adapter_safe_defaults(self):
        """Config adapter should provide safe LLM defaults"""
        from src.config.config_adapter import config_adapter
        cfg = config_adapter.get_effective_config()
        
        # Should have LLM keys but with safe values
        assert "llm_provider" in cfg
        assert "llm_model_name" in cfg
        
        # In minimal mode, these should be placeholder values
        llm_provider = cfg["llm_provider"]
        assert llm_provider in ("disabled", "openai"), (
            f"Expected 'disabled' or 'openai', got: {llm_provider}"
        )


@pytest.mark.ci_safe
class TestMinimalEnvironmentRequirements:
    """Test requirements-minimal.txt integrity"""
    
    def test_requirements_minimal_exists(self):
        """requirements-minimal.txt should exist"""
        req_file = Path("requirements-minimal.txt")
        assert req_file.exists(), "requirements-minimal.txt not found"
        
    def test_requirements_minimal_no_llm_packages(self):
        """requirements-minimal.txt should have no LLM packages"""
        forbidden = {
            "langchain", "openai", "anthropic", "browser-use", 
            "mem0", "faiss", "ollama"
        }
        
        req_file = Path("requirements-minimal.txt")
        with open(req_file) as f:
            lines = f.readlines()
            
        packages = {
            line.split("==")[0].split(">=")[0].strip().lower()
            for line in lines
            if line.strip() and not line.startswith("#")
        }
        
        found_forbidden = packages & forbidden
        assert len(found_forbidden) == 0, (
            f"Found forbidden packages in requirements-minimal.txt: {found_forbidden}"
        )
        
    def test_requirements_minimal_has_core_packages(self):
        """requirements-minimal.txt should have essential packages"""
        required_core = {"playwright", "gradio", "pyyaml"}
        
        req_file = Path("requirements-minimal.txt")
        with open(req_file) as f:
            lines = f.readlines()
            
        packages = {
            line.split("==")[0].split(">=")[0].strip().lower()
            for line in lines
            if line.strip() and not line.startswith("#")
        }
        
        missing = required_core - packages
        assert len(missing) == 0, (
            f"Missing core packages in requirements-minimal.txt: {missing}"
        )


# Pytest configuration
def pytest_configure(config):
    """Add custom markers"""
    config.addinivalue_line(
        "markers", 
        "minimal: tests that require ENABLE_LLM=false"
    )
