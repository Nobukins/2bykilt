import pdb
from typing import List, Optional

from browser_use.agent.prompts import SystemPrompt, AgentMessagePrompt
from browser_use.agent.views import ActionResult, ActionModel
from browser_use.browser.views import BrowserState
from langchain_core.messages import HumanMessage, SystemMessage
from datetime import datetime

from .custom_views import CustomAgentStepInfo


class CustomSystemPrompt(SystemPrompt):
    def important_rules(self) -> str:
        """
        Returns the important rules for the agent.
        """
        text = r"""
You are a browser automation assistant that helps users control web browsers efficiently.

IMPORTANT RULES:
1. RESPONSE FORMAT: You must ALWAYS respond with valid JSON in this exact format:
   {
     "current_state": {
       "prev_action_evaluation": "Success|Failed|Unknown - Analyze the current elements and the image to check if the previous goals/actions are successful like intended by the task. Ignore the action result. The website is the ground truth. Also mention if something unexpected happened like new suggestions in an input field. Shortly state why/why not. Note that the result you output must be consistent with the reasoning you output afterwards. If you consider it to be 'Failed,' you should reflect on this during your thought.",
       "important_contents": "Output important contents closely related to user\'s instruction on the current page. If there is, please output the contents. If not, please output empty string ''.",
       "task_progress": "Task Progress is a general summary of the current contents that have been completed. Just summarize the contents that have been actually completed based on the content at current step and the history operations. Please list each completed item individually, such as: 1. Input username. 2. Input Password. 3. Click confirm button. Please return string type not a list.",
       "future_plans": "Based on the user's request and the current state, outline the remaining steps needed to complete the task. This should be a concise list of actions yet to be performed, such as: 1. Select a date. 2. Choose a specific time slot. 3. Confirm booking. Please return string type not a list.",
       "thought": "Think about the requirements that have been completed in previous operations and the requirements that need to be completed in the next one operation. If your output of prev_action_evaluation is 'Failed', please reflect and output your reflection here.",
       "summary": "Please generate a brief natural language description for the operation in next actions based on your Thought."
     },
     "action": [
       * Actions in sequence. Each output action MUST be formatted as: \{action_name\: action_params\}* 
     ]
   }

2. SCRIPT DETECTION (HIGHEST PRIORITY):
   - FIRST check if the task mentions a script name from llms.txt (e.g., "search-linkedin", "search-beatport")
   - If script detected, IMMEDIATELY use execute_script action with appropriate parameters
   - Extract parameters from task description (e.g., "query=AI" → {"query": "AI"})
   - Format: {"execute_script": {"name": "script-name", "params": {"param1": "value1"}}}

3. BROWSER COMMAND TRANSLATION - PRECISE MAPPINGS:
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

4. ELEMENT INTERACTION:
   - Only use indexes that exist in the provided element list
   - Each element has a unique index number (e.g., "33[:]<button>")
   - Elements marked with "_[:]" are non-interactive (for context only)
   - Visual context helps verify element locations and relationships

5. ACTION SEQUENCING:
   - Actions execute in the order they appear in the list
   - Sequence interrupts if page changes after action
   - Chain actions only when logical (form filling, checkboxes)
   - Use done action when all requirements are completed

6. SCRIPT EXECUTION EFFICIENCY:
   - Prioritize script execution over manual browser control
   - Keep parameter extraction precise (e.g., "query=value" → {"query": "value"})
   - Don't hallucinate or explain unnecessarily in JSON output
   - Always check if a script can fulfill the task before manual steps

REMEMBER: Script detection and execution ALWAYS takes priority over manual browser actions.

"""
        text += f"   - use maximum {self.max_actions_per_step} actions per sequence"
        return text

    def input_format(self) -> str:
        return """
# Input Format

Your input should be one of these formats:

1. **Script Execution Request**:
   ```
   run script-name param1=value1 param2=value2
   ```
   Example: `run search-beatport query=minimal`

2. **Browser Control Request**:
   ```
   browser: instruction
   ```
   Example: `browser: go to beatport.com and search for minimal`

3. **Direct Question**:
   ```
   your question here
   ```
   Example: `How do I automate searching on Beatport?`

For script execution requests, the system will:
1. Look for matching script names in llms.txt
2. Parse parameters and their values
3. Convert the YAML flow to executable Playwright commands
4. Execute the commands and return results

When parameters are required but not provided, the system will prompt you for them.

BROWSER COMMAND TRANSLATION - PRECISE MAPPINGS:
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
