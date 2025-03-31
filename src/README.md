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

# 2Bykilt Source Modules

This directory contains the core modules of the 2Bykilt application.

## Module Overview

### Command Dispatcher

The `CommandDispatcher` (in `modules/command_dispatcher.py`) parses user prompts, identifies the appropriate action type, and delegates execution to specialized handlers. Features include:

- Circular reference detection to prevent infinite recursion
- Action type registration system for extensibility
- Parameter extraction from user prompts
- Fallback to LLM for unknown commands

### Action Translator

The `ActionTranslator` (in `config/action_translator.py`) converts actions defined in the `llms.txt` file into JSON-based command structures for execution. Features include:

- Support for multiple action types (browser-control, unlock-future)
- Parameter substitution using `${params.name}` syntax
- Input validation to ensure required fields like URLs are present
- JSON serialization with proper error handling

### Script Manager

The `script_manager.py` module handles the execution of different script types:

- **browser-control**: Generates and executes Playwright-based scripts
- **script**: Executes pytest-based scripts with parameter substitution
- **git-script**: Clones repositories and executes scripts from them
- **unlock-future**: Uses JSON-based execution for browser automation

### Execution Engines

Multiple execution engines provide different ways to control browsers:

- `ExecutionDebugEngine`: JSON-based command execution with detailed logging
- `ExecutionEngine`: Traditional script-based execution

## Available Action Types

| Type | Description | File |
|------|-------------|------|
| browser-control | Traditional browser automation with Playwright | script_manager.py |
| script | Direct execution of pytest scripts | script_manager.py |
| git-script | Clone and execute scripts from git repositories | script_manager.py |
| unlock-future | JSON-based browser automation | execution_debug_engine.py |

## Feature: Parameter Substitution

Actions can define parameters that users provide at runtime. The syntax `${params.name}` is used to insert these parameters into commands, URLs, or form values.

---

# 2bykilt 魔法の源泉

<img src="../assets/2bykilt-magic-source.png" alt="2Bykilt 魔法の源泉" width="200"/>

## 魔導士の研究書

ここには**2bykilt**の魔法の源泉となるコードが収められています。この秘伝の魔法書を理解することで、より強力な業務効率化の魔法を唱えることができるでしょう！

## 魔法の構成要素

### 🧙‍♂️ `/agent` - 魔法使いの召喚
魔法使い（エージェント）の召喚と操作を担当します。様々な魔法使いを呼び出し、ブラウザという世界を探索させることができます。

### 🔮 `/browser` - 魔法の窓
ブラウザという「魔法の窓」を操る術を提供します。この窓を通して、インターネットの世界へと干渉することができます。

### 📜 `/config` - 魔法の設定書
`llms.txt`という魔法の設定書を解読し、どのような魔法が使えるかを判断します。

### 🎮 `/controller` - 魔法の操り手
ブラウザを細かく操作するための術を提供します。高度な魔法を実行する際の細かい動きをコントロールします。

### ⚡ `/modules` - 魔法の結晶
特殊な魔法の力を秘めた結晶たち。それぞれが独自の力を持ち、組み合わせることでより強力な魔法を生み出します。

### 📊 `/script` - 魔法の書
あらかじめ用意された魔法の呪文（スクリプト）を管理します。これらの呪文は何度でも唱えることができ、複雑な作業を自動化します。

### 🖥️ `/ui` - 魔法の鏡
魔法の実行状況を映し出す鏡。魔法の進行状況をリアルタイムで確認することができます。

### 🛠️ `/utils` - 魔法の道具箱
魔法を使う上で便利な道具たちが収められています。これらを使いこなすことで、より効率的に魔法を操ることができます。

## 魔法の使い方

1. **魔法の準備**: アプリケーションは `webui.py` または `bykilt.py` から始まります。
2. **魔法使いの選択**: Gradioの魔法陣からエージェントを設定し起動します。
3. **魔法の実行**: 選ばれたエージェントが `agent_manager.py` を通じて召喚され実行されます。
4. **魔法の窓への干渉**: エージェントはPlaywrightを使ってブラウザという窓を通じてWebページに干渉します。
5. **魔法の結果**: 結果はリアルタイムでUIに表示されます。
6. **魔法の記録**: 完了したタスクは録画、トレース、履歴として保存されます。

*「バイキルト」の力を2倍に高めた2bykiltで、あなたの魔法使いとしての力を最大限に引き出しましょう！*