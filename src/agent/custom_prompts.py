import pdb
from typing import List, Optional
import os

# LLM機能の有効/無効を制御
ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"

# 条件付きLLMインポート
if ENABLE_LLM:
    try:
        from browser_use.agent.prompts import SystemPrompt, AgentMessagePrompt
        from browser_use.agent.views import ActionResult, ActionModel
        from browser_use.browser.views import BrowserState
        from langchain_core.messages import HumanMessage, SystemMessage
        from datetime import datetime
        from .custom_views import CustomAgentStepInfo
        LLM_PROMPTS_AVAILABLE = True
    except ImportError as e:
        print(f"⚠️ Warning: LLM prompts modules failed to load: {e}")
        LLM_PROMPTS_AVAILABLE = False
        # ダミークラスを定義
        class SystemPrompt: pass
        class AgentMessagePrompt: pass
else:
    LLM_PROMPTS_AVAILABLE = False
    # ダミークラスを定義
    class SystemPrompt: pass
    class AgentMessagePrompt: pass


class CustomSystemPrompt(SystemPrompt):
    def important_rules(self) -> str:
        """
        Returns the important rules for the agent.
        """
        text = r"""
1. RESPONSE FORMAT: You must ALWAYS respond with valid JSON in this exact format:
   {
     "current_state": {
       "prev_action_evaluation": "Success|Failed|Unknown"
(Analyze current elements and image to verify if previous actions succeeded as intended. The website is the ground truth. Mention unexpected events like new suggestions in input fields.),
       "important_contents": "Output important contents related to user's instruction on the current page. If none, output empty string ''.",
       "task_progress": "Summarize completed steps based on current state and history. Format as numbered list: 1. Step one. 2. Step two. Return as string.",
       "future_plans": "Outline remaining steps needed to complete the task. Format as numbered list: 1. Next step. 2. Following step. Return as string.",
       "thought": "Analyze completed requirements and next requirements. If prev_action_evaluation is 'Failed', include reflection here.",
       "summary": "Generate brief natural language description for the next actions based on your Thought."
     },
     "action": [
       * Actions to execute in sequence. Each output action MUST be formatted as: {action_name: action_params}* 
     ]
   }

2. DECISION PRIORITY ORDER - ALWAYS follow this exact sequence:
   a) SCRIPT EXECUTION: If task matches llms.txt script, immediately execute script
   b) BROWSER NAVIGATION: If URL needed, use go_to_url
   c) FORM INTERACTION: For inputs and clicks on visible elements
   d) EXTRACTION: For collecting information
   e) COMPLETION: Use done when requirements fulfilled

3. ACTION FORMATTING - Use these EXACT formats:
   - script: {"execute_script": {"name": "script_name", "params": {"param1": "value1"}}}
     → First step if script detection possible
   
   - navigate: {"go_to_url": {"url": "https://example.com"}} 
     → Exact URL as provided, no modifications
   
   - click: {"click_element": {"index": 5}} 
     → Use only the index number from element list
   
   - fill: {"input_text": {"index": 2, "text": "search term"}} 
     → First param is index, second is exact text from user input
   
   - extract: {"extract_page_content": {}} 
     → Use to collect information from current page
   
   - done: {"done": {"message": "Task completed successfully"}} 
     → Use when all requirements are fulfilled

4. SCRIPT DETECTION RULES:
   - ALWAYS check first if task can be handled by a script
   - Keywords like "run", "execute", or direct script names trigger script execution
   - Format: {"execute_script": {"name": "script_name", "params": {"param1": "value1"}}}
   - Common scripts: search-google, search-linkedin, search-beatport
   - Extract parameters precisely from user input (e.g., "query=value" → {"query": "value"})
   - Script execution takes absolute priority over manual browser control

5. BROWSER CONTROL RULES:
   - Only use after confirming task can't be handled by script execution
   - Only use element indexes that exist in the provided element list
   - Chain actions only when logically connected (form filling, checkboxes)
   - Minimize actions by combining steps when possible
   - If page changes after action, the sequence is interrupted

6. ERROR PREVENTION:
   - Don't hallucinate elements or scripts that don't exist
   - Verify element indices before interaction
   - Prefer script execution over complex manual sequences
   - Always use done action when all requirements are completed
   - If stuck or encountering errors, prioritize extraction then completion

7. CRITICAL PERFORMANCE RULES:
   - Make decisions IMMEDIATELY - don't overthink
   - NEVER explain your reasoning in the JSON output
   - If task mentions script name, execute it WITHOUT manual browser actions
   - Keep JSON responses precise and minimal
   - Always finalize with done action when requirements are met

"""
        text += f"   - use maximum {self.max_actions_per_step} actions per sequence"
        return text

    def input_format(self) -> str:
        return """
# Input Format

Your input will be processed according to these strict rules:

## INPUT PATTERN RECOGNITION - ALWAYS check in this exact order:

1. **SCRIPT EXECUTION REQUEST** (HIGHEST PRIORITY):
   - Format: `run script-name param1=value1 param2=value2`
   - Examples: 
     * `run search-beatport query=minimal`
     * `search-linkedin query="AI developer"`
     * `execute search-google query="browser automation"`
   
   - IMMEDIATE ACTION: Convert directly to script execution JSON:
     ```json
     {"execute_script": {"name": "script-name", "params": {"param1": "value1", "param2": "value2"}}}
     ```

2. **BROWSER CONTROL REQUEST**:
   - Format: `browser: instruction` or any navigation/search instruction
   - Examples:
     * `browser: go to beatport.com and search for minimal`
     * `go to google.com and search for AI tools`
   
   - ACTION: Break into minimal action sequence:
     ```json
     [{"go_to_url": {"url": "https://website.com"}}, {"input_text": {...}}, {"click_element": {...}}]
     ```

3. **DIRECT QUESTION**:
   - Format: Any input that doesn't match patterns 1-2
   - ACTION: Respond conversationally or suggest appropriate script

## PARAMETER EXTRACTION RULES:

1. **For script execution**:
   - Extract script name exactly as written
   - Parse parameters in format `param=value`
   - Handle quoted values properly: `query="multiple words"`
   - Common parameters:
     * query: Search term or query string
     * url: Target URL for operations
     * username/password: Login credentials
     * count: Number of items to process

2. **For browser control**:
   - Identify target website from input
   - Extract search terms or input values
   - Determine required actions (navigate, click, input)

## ACTION TRANSLATION REFERENCE:

- navigate: {"go_to_url": {"url": "https://example.com"}} 
  → Exact URL from user, no modifications

- click: {"click_element": {"index": 5}} 
  → Use only the index number from element list

- fill: {"input_text": {"index": 2, "text": "search term"}} 
  → First param is index, second is exact text from user input

- extract: {"extract_page_content": {}} 
  → Use to collect information from current page

- done: {"done": {"message": "Task completed successfully"}} 
  → Use when all requirements are fulfilled

    """


class CustomAgentMessagePrompt(AgentMessagePrompt):
    def __init__(
            self,
            state: BrowserState,
            actions: Optional[List[ActionModel]] = None,
            result: Optional[List[ActionResult]] = None,
            include_attributes: list[str] = [],
            max_error_length: int = 400,
            step_info: Optional[CustomAgentStepInfo] = None,
    ):
        super(CustomAgentMessagePrompt, self).__init__(state=state,
                                                       result=result,
                                                       include_attributes=include_attributes,
                                                       max_error_length=max_error_length,
                                                       step_info=step_info
                                                       )
        self.actions = actions

    def get_user_message(self, use_vision: bool = True) -> HumanMessage:
        if self.step_info:
            step_info_description = f'Current step: {self.step_info.step_number}/{self.step_info.max_steps}\n'
        else:
            step_info_description = ''

        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        step_info_description += f"Current date and time: {time_str}"

        elements_text = self.state.element_tree.clickable_elements_to_string(include_attributes=self.include_attributes)

        has_content_above = (self.state.pixels_above or 0) > 0
        has_content_below = (self.state.pixels_below or 0) > 0

        if elements_text != '':
            if has_content_above:
                elements_text = (
                    f'... {self.state.pixels_above} pixels above - scroll or extract content to see more ...\n{elements_text}'
                )
            else:
                elements_text = f'[Start of page]\n{elements_text}'
            if has_content_below:
                elements_text = (
                    f'{elements_text}\n... {self.state.pixels_below} pixels below - scroll or extract content to see more ...'
                )
            else:
                elements_text = f'{elements_text}\n[End of page]'
        else:
            elements_text = 'empty page'

        state_description = f"""
{step_info_description}
1. Task: {self.step_info.task}. 
2. Hints(Optional): 
{self.step_info.add_infos}
3. Memory: 
{self.step_info.memory}
4. Current url: {self.state.url}
5. Available tabs:
{self.state.tabs}
6. Interactive elements:
{elements_text}
        """

        if self.actions and self.result:
            state_description += "\n **Previous Actions** \n"
            state_description += f'Previous step: {self.step_info.step_number-1}/{self.step_info.max_steps} \n'
            for i, result in enumerate(self.result):
                action = self.actions[i]
                state_description += f"Previous action {i + 1}/{len(self.result)}: {action.model_dump_json(exclude_unset=True)}\n"
                if result.include_in_memory:
                    if result.extracted_content:
                        state_description += f"Result of previous action {i + 1}/{len(self.result)}: {result.extracted_content}\n"
                    if result.error:
                        # only use last 300 characters of error
                        error = result.error[-self.max_error_length:]
                        state_description += (
                            f"Error of previous action {i + 1}/{len(self.result)}: ...{error}\n"
                        )

        if self.state.screenshot and use_vision == True:
            # Format message for vision model
            return HumanMessage(
                content=[
                    {'type': 'text', 'text': state_description},
                    {
                        'type': 'image_url',
                        'image_url': {'url': f'data:image/png;base64,{self.state.screenshot}'},
                    },
                ]
            )

        return HumanMessage(content=state_description)
