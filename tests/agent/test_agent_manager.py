"""
Tests for agent_manager module (Issue #340 Phase 3)

Coverage targets:
- evaluate_prompt_unified
- extract_params_unified
- resolve_env_variables_unified

Target: Agent 2% → 30% coverage
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any, Optional

# Set ENABLE_LLM before importing agent_manager
os.environ['ENABLE_LLM'] = 'true'

from src.agent.agent_manager import (
    evaluate_prompt_unified,
    extract_params_unified,
    resolve_env_variables_unified,
    stop_agent,
    stop_research_agent
)


class TestEvaluatePromptUnified:
    """Test evaluate_prompt_unified function"""
    
    def test_evaluate_with_standalone_result(self):
        """Test evaluation when standalone evaluator finds command"""
        with patch('src.agent.agent_manager.pre_evaluate_prompt_standalone') as mock_standalone:
            mock_standalone.return_value = {
                "name": "test_command",
                "params": {"key": "value"}
            }
            
            result = evaluate_prompt_unified("run test command")
            
            assert result is not None
            assert result["name"] == "test_command"
            assert result["params"]["key"] == "value"
            mock_standalone.assert_called_once_with("run test command")
    
    def test_evaluate_standalone_not_found_llm_disabled(self):
        """Test evaluation when standalone not found and LLM disabled"""
        with patch('src.agent.agent_manager.pre_evaluate_prompt_standalone', return_value=None), \
             patch('src.agent.agent_manager.ENABLE_LLM', False):
            
            result = evaluate_prompt_unified("unknown command")
            
            assert result is None
    
    def test_evaluate_standalone_not_found_llm_enabled(self):
        """Test evaluation when standalone not found but LLM finds it"""
        with patch('src.agent.agent_manager.pre_evaluate_prompt_standalone', return_value=None), \
             patch('src.agent.agent_manager.ENABLE_LLM', True), \
             patch('src.agent.agent_manager.LLM_AGENT_AVAILABLE', True), \
             patch('src.agent.agent_manager.pre_evaluate_prompt') as mock_llm:
            
            mock_llm.return_value = {
                "name": "llm_command",
                "params": {}
            }
            
            result = evaluate_prompt_unified("complex command")
            
            assert result is not None
            assert result["name"] == "llm_command"
            mock_llm.assert_called_once_with("complex command")
    
    def test_evaluate_llm_exception(self):
        """Test evaluation when LLM raises exception"""
        with patch('src.agent.agent_manager.pre_evaluate_prompt_standalone', return_value=None), \
             patch('src.agent.agent_manager.ENABLE_LLM', True), \
             patch('src.agent.agent_manager.LLM_AGENT_AVAILABLE', True), \
             patch('src.agent.agent_manager.pre_evaluate_prompt', side_effect=RuntimeError("LLM error")), \
             patch('builtins.print') as mock_print:
            
            result = evaluate_prompt_unified("command")
            
            assert result is None
            # Check that warning was printed
            assert mock_print.called
    
    def test_evaluate_both_not_found(self):
        """Test evaluation when both standalone and LLM return None"""
        with patch('src.agent.agent_manager.pre_evaluate_prompt_standalone', return_value=None), \
             patch('src.agent.agent_manager.ENABLE_LLM', True), \
             patch('src.agent.agent_manager.LLM_AGENT_AVAILABLE', True), \
             patch('src.agent.agent_manager.pre_evaluate_prompt', return_value=None):
            
            result = evaluate_prompt_unified("unknown")
            
            assert result is None


class TestExtractParamsUnified:
    """Test extract_params_unified function"""
    
    def test_extract_with_standalone_params(self):
        """Test parameter extraction via standalone"""
        with patch('src.agent.agent_manager.extract_params_standalone') as mock_standalone:
            mock_standalone.return_value = {
                "url": "https://example.com",
                "selector": "div.content"
            }
            
            result = extract_params_unified("go to https://example.com", ["url", "selector"])
            
            assert result["url"] == "https://example.com"
            assert result["selector"] == "div.content"
            mock_standalone.assert_called_once()
    
    def test_extract_standalone_empty_llm_disabled(self):
        """Test extraction when standalone returns empty and LLM disabled"""
        with patch('src.agent.agent_manager.extract_params_standalone', return_value={}), \
             patch('src.agent.agent_manager.ENABLE_LLM', False):
            
            result = extract_params_unified("command", ["param1"])
            
            assert result == {}
    
    def test_extract_standalone_empty_llm_enabled(self):
        """Test extraction when standalone empty but LLM extracts"""
        with patch('src.agent.agent_manager.extract_params_standalone', return_value={}), \
             patch('src.agent.agent_manager.ENABLE_LLM', True), \
             patch('src.agent.agent_manager.LLM_AGENT_AVAILABLE', True), \
             patch('src.agent.agent_manager.extract_params') as mock_llm:
            
            mock_llm.return_value = {"param1": "value1"}
            
            result = extract_params_unified("command", ["param1"])
            
            assert result["param1"] == "value1"
            mock_llm.assert_called_once()
    
    def test_extract_llm_exception(self):
        """Test extraction when LLM raises exception"""
        with patch('src.agent.agent_manager.extract_params_standalone', return_value={}), \
             patch('src.agent.agent_manager.ENABLE_LLM', True), \
             patch('src.agent.agent_manager.LLM_AGENT_AVAILABLE', True), \
             patch('src.agent.agent_manager.extract_params', side_effect=RuntimeError("LLM error")), \
             patch('builtins.print') as mock_print:
            
            result = extract_params_unified("command", ["param1"])
            
            assert result == {}
            assert mock_print.called
    
    def test_extract_with_partial_standalone(self):
        """Test extraction when standalone returns partial params"""
        with patch('src.agent.agent_manager.extract_params_standalone') as mock_standalone:
            mock_standalone.return_value = {"url": "https://example.com"}
            
            result = extract_params_unified("go to site", ["url", "timeout"])
            
            # Should return what standalone found
            assert result["url"] == "https://example.com"
            # Should not have timeout if standalone didn't extract it
            assert "timeout" not in result or result["timeout"] is None


class TestResolveEnvVariablesUnified:
    """Test resolve_env_variables_unified function"""
    
    def test_resolve_with_standalone(self):
        """Test environment variable resolution via standalone"""
        with patch('src.agent.agent_manager.resolve_sensitive_env_variables_standalone') as mock_standalone:
            mock_standalone.return_value = "https://api.example.com/v1"
            
            with patch('src.agent.agent_manager.ENABLE_LLM', False):
                result = resolve_env_variables_unified("${API_URL}")
            
            assert result == "https://api.example.com/v1"
            mock_standalone.assert_called_once_with("${API_URL}")
    
    def test_resolve_with_standalone_then_llm(self):
        """Test resolution via standalone then LLM enhancement"""
        with patch('src.agent.agent_manager.resolve_sensitive_env_variables_standalone') as mock_standalone, \
             patch('src.agent.agent_manager.ENABLE_LLM', True), \
             patch('src.agent.agent_manager.LLM_AGENT_AVAILABLE', True), \
             patch('src.agent.agent_manager.resolve_sensitive_env_variables') as mock_llm:
            
            mock_standalone.return_value = "https://api.example.com"
            mock_llm.return_value = "https://api.example.com/enhanced"
            
            result = resolve_env_variables_unified("${API_URL}")
            
            assert result == "https://api.example.com/enhanced"
            mock_standalone.assert_called_once_with("${API_URL}")
            mock_llm.assert_called_once_with("https://api.example.com")
    
    def test_resolve_llm_exception(self):
        """Test resolution when LLM raises exception"""
        with patch('src.agent.agent_manager.resolve_sensitive_env_variables_standalone') as mock_standalone, \
             patch('src.agent.agent_manager.ENABLE_LLM', True), \
             patch('src.agent.agent_manager.LLM_AGENT_AVAILABLE', True), \
             patch('src.agent.agent_manager.resolve_sensitive_env_variables', side_effect=RuntimeError("LLM error")), \
             patch('builtins.print') as mock_print:
            
            mock_standalone.return_value = "fallback_value"
            
            result = resolve_env_variables_unified("${VAR}")
            
            # Should return standalone result when LLM fails
            assert result == "fallback_value"
            assert mock_print.called
    
    def test_resolve_no_variables(self):
        """Test resolution with plain text (no variables)"""
        with patch('src.agent.agent_manager.resolve_sensitive_env_variables_standalone') as mock_standalone:
            mock_standalone.return_value = "plain text"
            
            with patch('src.agent.agent_manager.ENABLE_LLM', False):
                result = resolve_env_variables_unified("plain text")
            
            assert result == "plain text"
    
    def test_resolve_multiple_variables(self):
        """Test resolution with multiple environment variables"""
        with patch('src.agent.agent_manager.resolve_sensitive_env_variables_standalone') as mock_standalone:
            mock_standalone.return_value = "https://user:pass@example.com/path"
            
            with patch('src.agent.agent_manager.ENABLE_LLM', False):
                result = resolve_env_variables_unified("${API_URL}/${API_KEY}")
            
            assert result == "https://user:pass@example.com/path"
            mock_standalone.assert_called_once()


class TestStopAgent:
    """Tests for stop_agent function"""
    
    @pytest.mark.asyncio
    async def test_stop_agent_success(self):
        """Test successful agent stop"""
        mock_agent = MagicMock()
        mock_agent.stop = MagicMock()
        
        with patch('src.agent.agent_manager._global_agent', mock_agent), \
             patch('gradio.update') as mock_gr_update:
            
            mock_gr_update.return_value = MagicMock()
            
            result = await stop_agent()
            
            # Should call stop on agent
            mock_agent.stop.assert_called_once()
            
            # Should return message and UI updates
            assert len(result) == 3
            assert "Stop requested" in result[0]
    
    @pytest.mark.asyncio
    async def test_stop_agent_exception(self):
        """Test agent stop with exception"""
        mock_agent = MagicMock()
        mock_agent.stop = MagicMock(side_effect=Exception("Agent not running"))
        
        with patch('src.agent.agent_manager._global_agent', mock_agent), \
             patch('gradio.update') as mock_gr_update:
            
            mock_gr_update.return_value = MagicMock()
            
            result = await stop_agent()
            
            # Should return error message
            assert len(result) == 3
            assert "Error during stop" in result[0]
    
    @pytest.mark.asyncio
    async def test_stop_agent_ui_updates(self):
        """Test stop_agent returns correct UI updates"""
        mock_agent = MagicMock()
        mock_agent.stop = MagicMock()
        
        with patch('src.agent.agent_manager._global_agent', mock_agent), \
             patch('gradio.update') as mock_gr_update:
            
            mock_update_obj = MagicMock()
            mock_gr_update.return_value = mock_update_obj
            
            result = await stop_agent()
            
            # Should call gr.update for UI elements
            assert mock_gr_update.call_count >= 2
            assert result[1] == mock_update_obj
            assert result[2] == mock_update_obj


class TestStopResearchAgent:
    """Tests for stop_research_agent function"""
    
    @pytest.mark.asyncio
    async def test_stop_research_agent_success(self):
        """Test successful research agent stop"""
        mock_state = MagicMock()
        mock_state.request_stop = MagicMock()
        
        with patch('src.agent.agent_manager._global_agent_state', mock_state), \
             patch('gradio.update') as mock_gr_update:
            
            mock_gr_update.return_value = MagicMock()
            
            result = await stop_research_agent()
            
            # Should call request_stop on state
            mock_state.request_stop.assert_called_once()
            
            # Should return UI updates
            assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_stop_research_agent_exception(self):
        """Test research agent stop with exception"""
        mock_state = MagicMock()
        mock_state.request_stop = MagicMock(side_effect=Exception("State error"))
        
        with patch('src.agent.agent_manager._global_agent_state', mock_state), \
             patch('gradio.update') as mock_gr_update:
            
            mock_gr_update.return_value = MagicMock()
            
            result = await stop_research_agent()
            
            # Should return UI updates with error state
            assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_stop_research_agent_ui_updates(self):
        """Test stop_research_agent returns correct UI updates"""
        mock_state = MagicMock()
        mock_state.request_stop = MagicMock()
        
        with patch('src.agent.agent_manager._global_agent_state', mock_state), \
             patch('gradio.update') as mock_gr_update:
            
            mock_update_obj = MagicMock()
            mock_gr_update.return_value = mock_update_obj
            
            result = await stop_research_agent()
            
            # Should call gr.update for UI elements
            assert mock_gr_update.call_count >= 2
            assert result[0] == mock_update_obj
            assert result[1] == mock_update_obj
