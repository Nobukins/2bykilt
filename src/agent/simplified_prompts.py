import json

class WebAutomator:
    def __init__(self):
        self.current_state = {
            "prev_action_evaluation": "Unknown",
            "important_contents": "",
            "task_progress": "",
            "future_plans": "",
            "thought": "",
            "summary": ""
        }
        self.actions = []
        
    def set_state(self, key, value):
        """Set a specific state value"""
        if key in self.current_state:
            self.current_state[key] = value
        else:
            print(f"Warning: Unknown state key '{key}'")
    
    def add_action(self, action_name, params):
        """Add an action to the sequence"""
        self.actions.append({action_name: params})
    
    def clear_actions(self):
        """Clear all actions"""
        self.actions = []
        
    def get_response(self):
        """Get formatted JSON response"""
        return json.dumps({
            "current_state": self.current_state,
            "action": self.actions
        }, indent=2)
    
    def execute(self):
        """Simulate action execution (for debugging)"""
        print("Executing actions:")
        for action in self.actions:
            action_name = list(action.keys())[0]
            params = action[action_name]
            print(f"- {action_name}: {params}")
        return "Execution completed (simulation)"

# Example usage
def run_example():
    automator = WebAutomator()
    
    # Set state
    automator.set_state("prev_action_evaluation", "Success - Login form found")
    automator.set_state("task_progress", "1. Navigated to login page")
    automator.set_state("future_plans", "1. Enter username. 2. Enter password. 3. Click login")
    
    # Add actions
    automator.add_action("input_text", {"index": 1, "text": "testuser"})
    automator.add_action("input_text", {"index": 2, "text": "password123"})
    automator.add_action("click_element", {"index": 3})
    
    # Get response
    response = automator.get_response()
    print("\nJSON Response:")
    print(response)
    
    # Execute (simulation)
    result = automator.execute()
    print(f"\nResult: {result}")

if __name__ == "__main__":
    run_example()