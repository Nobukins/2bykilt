class WorkflowBuilder:
    """
    ドラッグ&ドロップでワークフローを構築するクラス
    - 一般的な操作を視覚的にチェーン
    - 条件分岐とループの組み込み
    - エラーハンドリングの追加
    """
    
    def __init__(self):
        self.workflow = []

    def add_action(self, action):
        self.workflow.append(action)

    def add_condition(self, condition):
        self.workflow.append(condition)

    def build(self):
        return self.workflow

    def debug_run(self, headless=True, slow_mo=0, highlight_elements=False):
        """
        Debug the workflow.
        :param headless: Run in headless mode.
        :param slow_mo: Slow down execution for debugging.
        :param highlight_elements: Highlight elements during execution.
        """
        print(f"Debugging workflow: {self.workflow}")
        # Add more detailed debugging logic here
        # ...
