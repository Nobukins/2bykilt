"""Module for managing global variables across the application"""
import logging
from src.utils.agent_state import AgentState

# Configure logging
logger = logging.getLogger(__name__)

# Global state variables
_global_browser = None
_global_browser_context = None
_global_agent = None
_global_agent_state = AgentState()

def get_globals():
    """Get global variables for use in other modules"""
    return {
        "browser": _global_browser,
        "browser_context": _global_browser_context,
        "agent": _global_agent,
        "agent_state": _global_agent_state
    }
