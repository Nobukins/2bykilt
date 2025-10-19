"""
Tests for LLM Service Gateway

This module tests the LLM service gateway functionality including:
- Gateway initialization
- LLM invocation
- Error handling
- Enable/disable logic
- Stub and Docker implementations
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from src.llm.service_gateway import (
    LLMServiceGateway,
    LLMServiceGatewayStub,
    DockerLLMServiceGateway,
    LLMServiceError,
    get_llm_gateway,
    reset_llm_gateway,
)


@pytest.mark.ci_safe
class TestLLMServiceGatewayStub:
    """Test cases for LLMServiceGatewayStub"""

    @pytest.fixture
    def stub_enabled(self):
        """Create stub with LLM enabled"""
        with patch.dict(os.environ, {"ENABLE_LLM": "true"}):
            return LLMServiceGatewayStub()

    @pytest.fixture
    def stub_disabled(self):
        """Create stub with LLM disabled"""
        with patch.dict(os.environ, {"ENABLE_LLM": "false"}):
            return LLMServiceGatewayStub()

    async def test_initialize_disabled(self, stub_disabled):
        """Test initialization when LLM is disabled"""
        await stub_disabled.initialize()
        assert stub_disabled._initialized is True
        assert stub_disabled.is_enabled() is False

    async def test_initialize_enabled(self, stub_enabled):
        """Test initialization when LLM is enabled"""
        await stub_enabled.initialize()
        assert stub_enabled._initialized is True
        assert stub_enabled.is_enabled() is True

    async def test_invoke_llm_not_initialized(self, stub_enabled):
        """Test LLM invocation before initialization raises error"""
        with pytest.raises(LLMServiceError, match="Gateway not initialized"):
            await stub_enabled.invoke_llm("test prompt")

    async def test_invoke_llm_disabled(self, stub_disabled):
        """Test LLM invocation when disabled returns empty response"""
        await stub_disabled.initialize()
        
        result = await stub_disabled.invoke_llm("test prompt")
        
        assert result["text"] == ""
        assert result["usage"] == {}
        assert result["disabled"] is True

    async def test_invoke_llm_enabled_stub(self, stub_enabled):
        """Test LLM invocation when enabled returns stub response"""
        await stub_enabled.initialize()
        
        result = await stub_enabled.invoke_llm("test prompt with multiple words")
        
        assert "text" in result
        assert result["text"] == "(LLM response placeholder - Phase3 implementation pending)"
        assert "usage" in result
        assert result["usage"]["prompt_tokens"] == 5  # "test prompt with multiple words"
        assert result["usage"]["completion_tokens"] == 10
        assert result["stub"] is True

    async def test_invoke_llm_with_config(self, stub_enabled):
        """Test LLM invocation with configuration"""
        await stub_enabled.initialize()
        
        config = {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        result = await stub_enabled.invoke_llm("test prompt", config=config)
        
        assert "text" in result
        assert "usage" in result

    async def test_shutdown_disabled(self, stub_disabled):
        """Test shutdown when LLM is disabled"""
        await stub_disabled.initialize()
        await stub_disabled.shutdown()
        
        assert stub_disabled._initialized is False

    async def test_shutdown_enabled(self, stub_enabled):
        """Test shutdown when LLM is enabled"""
        await stub_enabled.initialize()
        await stub_enabled.shutdown()
        
        assert stub_enabled._initialized is False

    async def test_multiple_invocations(self, stub_enabled):
        """Test multiple LLM invocations work correctly"""
        await stub_enabled.initialize()
        
        result1 = await stub_enabled.invoke_llm("first prompt")
        result2 = await stub_enabled.invoke_llm("second prompt")
        
        assert result1["text"] == result2["text"]  # Both return same stub
        assert "usage" in result1
        assert "usage" in result2

    def test_is_enabled_true(self, stub_enabled):
        """Test is_enabled returns True when ENABLE_LLM=true"""
        assert stub_enabled.is_enabled() is True

    def test_is_enabled_false(self, stub_disabled):
        """Test is_enabled returns False when ENABLE_LLM=false"""
        assert stub_disabled.is_enabled() is False

    async def test_reinitialize(self, stub_enabled):
        """Test reinitialization works correctly"""
        await stub_enabled.initialize()
        await stub_enabled.shutdown()
        await stub_enabled.initialize()
        
        assert stub_enabled._initialized is True
        
        result = await stub_enabled.invoke_llm("test")
        assert "text" in result


@pytest.mark.ci_safe
class TestDockerLLMServiceGateway:
    """Test cases for DockerLLMServiceGateway"""

    @pytest.fixture
    def docker_gateway_enabled(self):
        """Create Docker gateway with LLM enabled"""
        with patch.dict(os.environ, {"ENABLE_LLM": "true"}):
            return DockerLLMServiceGateway()

    @pytest.fixture
    def docker_gateway_disabled(self):
        """Create Docker gateway with LLM disabled"""
        with patch.dict(os.environ, {"ENABLE_LLM": "false"}):
            return DockerLLMServiceGateway()

    async def test_initialize_disabled(self, docker_gateway_disabled):
        """Test Docker gateway initialization when disabled"""
        await docker_gateway_disabled.initialize()
        assert docker_gateway_disabled._initialized is True
        assert docker_gateway_disabled.is_enabled() is False

    @pytest.mark.skip(reason="Docker sandbox not yet fully implemented")
    async def test_initialize_enabled_with_sandbox(self, docker_gateway_enabled):
        """Test Docker gateway initialization with sandbox"""
        # This test requires Docker sandbox implementation
        pass

    @pytest.mark.skip(reason="Docker sandbox not yet fully implemented")
    async def test_invoke_llm_with_docker_sandbox(self, docker_gateway_enabled):
        """Test LLM invocation through Docker sandbox"""
        # This test requires Docker sandbox implementation
        pass

    @pytest.mark.skip(reason="Docker sandbox not yet fully implemented")
    async def test_shutdown_with_sandbox(self, docker_gateway_enabled):
        """Test shutdown stops Docker sandbox"""
        # This test requires Docker sandbox implementation
        pass

    async def test_invoke_llm_error_handling(self, docker_gateway_enabled):
        """Test error handling when Docker sandbox cannot be initialized"""
        # When ENABLE_LLM=true but docker_sandbox module blocks import,
        # initialization should fail with LLMServiceError
        with pytest.raises(LLMServiceError, match="Sandbox initialization failed"):
            await docker_gateway_enabled.initialize()


@pytest.mark.ci_safe
class TestGetLLMGateway:
    """Test cases for get_llm_gateway singleton function"""

    def test_get_llm_gateway_returns_instance(self):
        """Test get_llm_gateway returns a gateway instance"""
        reset_llm_gateway()
        with patch.dict(os.environ, {"ENABLE_LLM": "false"}):
            gateway = get_llm_gateway()
            assert gateway is not None
            assert isinstance(gateway, LLMServiceGateway)

    def test_get_llm_gateway_singleton(self):
        """Test get_llm_gateway returns same instance"""
        reset_llm_gateway()
        with patch.dict(os.environ, {"ENABLE_LLM": "false"}):
            gateway1 = get_llm_gateway()
            gateway2 = get_llm_gateway()
            assert gateway1 is gateway2

    def test_get_llm_gateway_with_docker(self):
        """Test get_llm_gateway with Docker enabled"""
        reset_llm_gateway()
        with patch.dict(os.environ, {"ENABLE_LLM": "true"}):
            with patch('src.llm.service_gateway.DockerLLMServiceGateway') as mock_docker:
                mock_docker.return_value = Mock(spec=DockerLLMServiceGateway)
                gateway = get_llm_gateway(use_docker=True)
                assert gateway is not None

    def test_reset_llm_gateway(self):
        """Test reset_llm_gateway clears singleton"""
        with patch.dict(os.environ, {"ENABLE_LLM": "false"}):
            gateway1 = get_llm_gateway()
            reset_llm_gateway()
            gateway2 = get_llm_gateway()
            # After reset, we get a new instance
            assert gateway1 is not gateway2


@pytest.mark.ci_safe
class TestLLMServiceError:
    """Test cases for LLMServiceError exception"""

    def test_error_creation(self):
        """Test LLMServiceError can be created"""
        error = LLMServiceError("Test error")
        assert str(error) == "Test error"

    def test_error_inheritance(self):
        """Test LLMServiceError inherits from Exception"""
        error = LLMServiceError("Test error")
        assert isinstance(error, Exception)

    def test_error_raising(self):
        """Test LLMServiceError can be raised"""
        with pytest.raises(LLMServiceError):
            raise LLMServiceError("Test error")


@pytest.mark.ci_safe
class TestEnvironmentVariableHandling:
    """Test environment variable handling"""

    @pytest.mark.parametrize("env_value,expected", [
        ("true", True),
        ("TRUE", True),
        ("True", True),
        ("false", False),
        ("FALSE", False),
        ("False", False),
        ("", False),
        ("invalid", False),
    ])
    def test_enable_llm_parsing(self, env_value, expected):
        """Test ENABLE_LLM environment variable parsing"""
        with patch.dict(os.environ, {"ENABLE_LLM": env_value}):
            stub = LLMServiceGatewayStub()
            assert stub.is_enabled() == expected

    def test_default_enable_llm(self):
        """Test default ENABLE_LLM value when not set"""
        with patch.dict(os.environ, {}, clear=True):
            stub = LLMServiceGatewayStub()
            assert stub.is_enabled() is False


@pytest.mark.ci_safe
class TestConcurrentAccess:
    """Test concurrent access to gateway"""

    @pytest.fixture
    def stub_enabled(self):
        """Create stub with LLM enabled"""
        with patch.dict(os.environ, {"ENABLE_LLM": "true"}):
            return LLMServiceGatewayStub()

    async def test_concurrent_invocations(self, stub_enabled):
        """Test multiple concurrent LLM invocations"""
        import asyncio
        
        await stub_enabled.initialize()
        
        async def invoke():
            return await stub_enabled.invoke_llm("concurrent test")
        
        # Run 10 concurrent invocations
        results = await asyncio.gather(*[invoke() for _ in range(10)])
        
        assert len(results) == 10
        for result in results:
            assert "text" in result
            assert "usage" in result

    async def test_initialize_shutdown_cycle(self, stub_enabled):
        """Test repeated initialize/shutdown cycles"""
        for _ in range(3):
            await stub_enabled.initialize()
            assert stub_enabled._initialized is True
            
            result = await stub_enabled.invoke_llm("test")
            assert result is not None
            
            await stub_enabled.shutdown()
            assert stub_enabled._initialized is False
