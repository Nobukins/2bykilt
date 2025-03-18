# 2Bykilt Project Structure

This document provides an overview of the 2Bykilt project's module structure and functionality.

## Directory Structure

### `/src/agent`
Contains the agent implementation for browser automation:
- `agent_manager.py`: Manages agent lifecycle (creation, execution, termination), handles different agent types (org/custom), and coordinates with browser instances.
- `custom_agent.py`: Enhanced implementation of browser automation agent with task-specific optimizations.
- `custom_prompts.py`: Custom system and agent message prompts for improved browser automation.
- `simplified_prompts.py`: Streamlined versions of prompts for specific use cases.

### `/src/browser`
Browser interaction and management:
- `browser_manager.py`: Handles browser lifecycle operations (creation, closing), configuration, and recording setup.
- `custom_browser.py`: Extended browser implementation with additional capabilities.
- `custom_context.py`: Custom browser context implementation for enhanced control.

### `/src/config`
Configuration and parsing functionality:
- `llms_parser.py`: Parses and processes LLM-related configurations, handles script detection and parameter extraction.

### `/src/controller`
Browser control components:
- `custom_controller.py`: Custom controller that manages browser interactions and action execution, translates high-level commands into browser actions.
- Additional controllers for specialized interaction patterns and browser manipulation techniques.
- Handles error recovery and retry mechanisms for robust browser automation.

### `/src/modules`
Specialized functional modules:
- Reusable, self-contained components that implement specific pieces of functionality.
- Task-specific implementations that can be used across different agent types.
- Extension modules that add capabilities to the core system.
- Integration modules for third-party services and APIs.

### `/src/script`
Script automation functionality:
- `script_manager.py`: Manages and executes predefined browser automation scripts with parameter substitution.

### `/src/ui`
User interface components:
- `stream_manager.py`: Manages streaming UI updates for the browser agent, provides real-time feedback during agent execution.

### `/src/utils`
Utility functions and supporting modules:
- `agent_state.py`: Manages agent execution state and control flow.
- `deep_research.py`: Implements deep research capabilities for complex information gathering.
- `default_config_settings.py`: Provides default configuration management and UI settings.
- `globals_manager.py`: Centralized management of global state variables to avoid circular dependencies.
- `utils.py`: General utility functions for the application.

## Workflow

1. The application starts in `webui.py` or `bykilt.py`, initializing the UI and configuration.
2. Users configure and launch agents through the Gradio interface.
3. The selected agent type (org/custom) is instantiated and executed via `agent_manager.py`.
4. Agents interact with web pages using Playwright through the browser abstraction layer.
5. Results are streamed back to the UI in real-time during execution.
6. Completed tasks generate recordings, traces, and history files for review.

## Extension Points

- Add new agent types by extending the base Agent class and registering in `agent_manager.py`
- Create new browser automation scripts by defining them in the `llms.txt` file
- Enhance prompting by modifying the prompt templates in `custom_prompts.py`
- Develop new functional modules in the `/src/modules` directory to extend capabilities