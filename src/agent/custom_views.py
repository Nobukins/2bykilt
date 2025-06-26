import os
from dataclasses import dataclass
from typing import Type, Optional

# LLM機能の有効/無効を制御
ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"

# 条件付きLLMインポート
if ENABLE_LLM:
    try:
        from browser_use.agent.views import AgentOutput
        from browser_use.controller.registry.views import ActionModel
        from pydantic import BaseModel, ConfigDict, Field, create_model
        LLM_AGENT_VIEWS_AVAILABLE = True
        print("✅ LLM agent views modules loaded successfully")
    except ImportError as e:
        print(f"⚠️ Warning: LLM agent views imports failed: {e}")
        LLM_AGENT_VIEWS_AVAILABLE = False
        
        # ダミークラスを定義
        class AgentOutput:
            pass
        class ActionModel:
            pass
        class BaseModel:
            pass
        class ConfigDict:
            pass
        def Field(*args, **kwargs):
            return None
        def create_model(*args, **kwargs):
            return None
else:
    LLM_AGENT_VIEWS_AVAILABLE = False
    print("ℹ️ LLM agent views functionality is disabled (ENABLE_LLM=false)")
    
    # ダミークラスを定義
    class AgentOutput:
        pass
    class ActionModel:
        pass
    class BaseModel:
        pass
    class ConfigDict:
        pass
    def Field(*args, **kwargs):
        return None
    def create_model(*args, **kwargs):
        return None

@dataclass
class CustomAgentStepInfo:
    step_number: int
    max_steps: int
    task: str
    add_infos: str
    memory: str
    task_progress: str
    future_plans: str

if ENABLE_LLM and LLM_AGENT_VIEWS_AVAILABLE:
    class CustomAgentBrain(BaseModel):
        """Current state of the agent"""

        prev_action_evaluation: str
        important_contents: str
        task_progress: str
        future_plans: str
        thought: str
        summary: str

    class CustomAgentOutput(AgentOutput):
        """Output model for agent

        @dev note: this model is extended with custom actions in AgentService. You can also use some fields that are not in this model as provided by the linter, as long as they are registered in the DynamicActions model.
        """

        model_config = ConfigDict(arbitrary_types_allowed=True)

        current_state: CustomAgentBrain
        action: list[ActionModel]

        @staticmethod
        def type_with_custom_actions(
            custom_actions: Type[ActionModel],
        ) -> Type["CustomAgentOutput"]:
            """Extend actions with custom actions"""
            return create_model(
                "CustomAgentOutput",
                __base__=CustomAgentOutput,
                action=(
                    list[custom_actions],
                    Field(...),
                ),  # Properly annotated field with no default
                __module__=CustomAgentOutput.__module__,
            )
else:
    # LLM無効時のダミークラス
    class CustomAgentBrain:
        def __init__(self, **kwargs):
            self.prev_action_evaluation = kwargs.get('prev_action_evaluation', '')
            self.important_contents = kwargs.get('important_contents', '')
            self.task_progress = kwargs.get('task_progress', '')
            self.future_plans = kwargs.get('future_plans', '')
            self.thought = kwargs.get('thought', '')
            self.summary = kwargs.get('summary', '')

    class CustomAgentOutput:
        def __init__(self, **kwargs):
            self.current_state = kwargs.get('current_state', CustomAgentBrain())
            self.action = kwargs.get('action', [])

        @staticmethod
        def type_with_custom_actions(custom_actions):
            return CustomAgentOutput
