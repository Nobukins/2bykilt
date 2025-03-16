class ActionTemplate:
    """
    再利用可能なアクションテンプレートを管理するクラス
    - 一般的なブラウザ操作テンプレート
    - ドメイン固有の操作テンプレート
    """
    
    def __init__(self):
        self.templates = {}

    def add_template(self, name, template):
        self.templates[name] = template

    def get_template(self, name):
        return self.templates.get(name, None)

    def debug(self, interactive=False, step_by_step=False, parameter_values=None):
        """
        Debug the action template.
        :param interactive: Enable interactive mode.
        :param step_by_step: Enable step-by-step execution.
        :param parameter_values: Parameters to use during debugging.
        """
        print(f"Debugging template: {self.name}")
        if parameter_values:
            print(f"Using parameters: {parameter_values}")
        # Add more detailed debugging logic here
        # ...
