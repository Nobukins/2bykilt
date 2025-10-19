<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->
- [x] Verify that the copilot-instructions.md file in the .github directory is created. *(Created via workspace setup on 2025-10-16.)*

- [ ] Clarify Project Requirements
	<!-- Ask for project type, language, and frameworks if not specified. Skip if already provided. -->

- [ ] Scaffold the Project
	<!--
	Ensure that the previous step has been marked as completed.
	Call project setup tool with projectType parameter.
	Run scaffolding command to create project files and folders.
	Use '.' as the working directory.
	If no appropriate projectType is available, search documentation using available tools.
	Otherwise, create the project structure manually using available file creation tools.
	-->

- [ ] Customize the Project
	<!--
	Verify that all previous steps have been completed successfully and you have marked the step as completed.
	Develop a plan to modify codebase according to user requirements.
	Apply modifications using appropriate tools and user-provided references.
	Skip this step for "Hello World" projects.
	-->

- [ ] Install Required Extensions
	<!-- ONLY install extensions provided mentioned in the get_project_setup_info. Skip this step otherwise and mark as completed. -->

- [ ] Compile the Project
	<!--
	Verify that all previous steps have been completed.
	Install any missing dependencies.
	Run diagnostics and resolve any issues.
	Check for markdown files in project folder for relevant instructions on how to do this.
	-->

- [ ] Create and Run Task
	<!--
	Verify that all previous steps have been completed.
	Check https://code.visualstudio.com/docs/debugtest/tasks to determine if the project needs a task. If so, use the create_and_run_task to create and launch a task based on package.json, README.md, and project structure.
	Skip this step otherwise.
	 -->

- [ ] Launch the Project
	<!--
	Verify that all previous steps have been completed.
	Prompt user for debug mode, launch only if confirmed.
	 -->

- [ ] Ensure Documentation is Complete
	<!--
	Verify that all previous steps have been completed.
	Verify that README.md and the copilot-instructions.md file in the .github directory exists and contains current project information.
	Clean up the copilot-instructions.md file in the .github directory by removing all HTML comments.
	 -->

<!--
## Execution Guidelines
PROGRESS TRACKING:
- If any tools are available to manage the above todo list, use it to track progress through this checklist.
- After completing each step, mark it complete and add a summary.
- Read current todo list status before starting each new step.

COMMUNICATION RULES:
- Avoid verbose explanations or printing full command outputs.
- If a step is skipped, state that briefly (e.g. "No extensions needed").
- Do not explain project structure unless asked.
- Keep explanations concise and focused.

DEVELOPMENT RULES:
- Use '.' as the working directory unless user specifies otherwise.
- Avoid adding media or external links unless explicitly requested.
- Use placeholders only with a note that they should be replaced.
- Use VS Code API tool only for VS Code extension projects.
- Once the project is created, it is already opened in Visual Studio Code—do not suggest commands to open this project in Visual Studio again.
- If the project setup information has additional rules, follow them strictly.

PRE-PUSH VALIDATION RULES (CRITICAL):
Before pushing any changes, ALWAYS run local validation to catch issues early:

1. **CI Environment Simulation** (For Python Projects with pytest):
   ```bash
   # Simulate CI environment conditions
   unset BYKILT_ENV  # Or equivalent environment variables
   export ENABLE_LLM="true"  # Or project-specific env vars
   
   # Run tests with same markers as CI
   python -m pytest -m "ci_safe" --cov=src --cov-report=term -v
   
   # Or for targeted test validation:
   python -m pytest path/to/modified/test_file.py -xvs
   ```

2. **Common Issues to Check Locally**:
   - **Indentation/Scope Issues**: Ensure all assertions are within their context manager blocks
   - **Mock Patching**: Verify patches are applied before code execution (use context managers, not decorators when order matters)
   - **Environment Variables**: Test with and without key environment variables set
   - **Import Timing**: Check for module-level variable evaluation issues
   
3. **Test-Specific Validations**:
   - If modifying config-related code: Test with `BYKILT_ENV` unset
   - If using context managers: Verify all dependent code is inside the `with` block
   - If patching module-level variables: Use context managers instead of decorators
   
4. **Fast Local Checks** (Before full CI simulation):
   ```bash
   # Run only modified test files
   python -m pytest tests/path/to/test_file.py -v
   
   # Check for obvious errors
   python -m pytest tests/path/to/test_file.py --collect-only
   ```

5. **Processing Time Awareness**:
   - Local single test file: ~5-10 seconds
   - Local full ci_safe suite: ~2-5 minutes
   - CI full suite: ~5-8 minutes
   - Budget time accordingly before pushing

**NEVER push without running at least the modified test files locally first.**
**If tests take >30 seconds locally, they will likely take 2-3 minutes in CI.**

FOLDER CREATION RULES:
- Always use the current directory as the project root.
- If you are running any terminal commands, use the '.' argument to ensure that the current working directory is used ALWAYS.
- Do not create a new folder unless the user explicitly requests it besides a .vscode folder for a tasks.json file.
- If any of the scaffolding commands mention that the folder name is not correct, let the user know to create a new folder with the correct name and then reopen it again in vscode.

EXTENSION INSTALLATION RULES:
- Only install extension specified by the get_project_setup_info tool. DO NOT INSTALL any other extensions.

PROJECT CONTENT RULES:
- If the user has not specified project details, assume they want a "Hello World" project as a starting point.
- Avoid adding links of any type (URLs, files, folders, etc.) or integrations that are not explicitly required.
- Avoid generating images, videos, or any other media files unless explicitly requested.
- If you need to use any media assets as placeholders, let the user know that these are placeholders and should be replaced with the actual assets later.
- Ensure all generated components serve a clear purpose within the user's requested workflow.
- If a feature is assumed but not confirmed, prompt the user for clarification before including it.
- If you are working on a VS Code extension, use the VS Code API tool with a query to find relevant VS Code API references and samples related to that query.

COMMON PITFALLS TO AVOID (Learned from Issue #340):

1. **Context Manager Scope Issues**:
   ```python
   # ❌ WRONG - Assertions outside context manager
   def test_something(self):
       with patch('module.VARIABLE', False):
           result = function_call()
       assert result == expected  # ← Patch already removed!
   
   # ✅ CORRECT - All dependent code inside context manager
   def test_something(self):
       with patch('module.VARIABLE', False):
           result = function_call()
           assert result == expected  # ← Patch still active
   ```

2. **Module-Level Variable Patching**:
   - Decorator-based `@patch()` may not work for module-level variables used in conditionals
   - Use context managers (`with patch()`) for better control over patch timing
   - Module-level variables are evaluated at import time, not function call time

3. **Environment-Specific Configuration**:
   - Default environments (e.g., 'development') may have different settings than expected
   - Always test with environment variables unset to simulate CI conditions
   - Config files in repository may cause multi-env systems to activate unexpectedly

4. **Indentation Matters**:
   - Python's whitespace-sensitive syntax can cause subtle bugs
   - One level of indentation difference = completely different scope
   - Always verify assertions are at the correct indentation level

TASK COMPLETION RULES:
- Your task is complete when:
  - Project is successfully scaffolded and compiled without errors
  - copilot-instructions.md file in the .github directory exists in the project
  - README.md file exists and is up to date
  - User is provided with clear instructions to debug/launch the project

Before starting a new task in the above plan, update progress in the plan.
-->
- Work through each checklist item systematically.
- Keep communication concise and focused.
- Follow development best practices.
