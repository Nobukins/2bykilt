"""
LLM非依存のプロンプト評価機能
事前登録されたコマンドの解析とパラメータ抽出を行います
"""
import re
import os
import yaml
from typing import Dict, List, Any, Optional, Union

def load_actions_config_standalone() -> Dict[str, Any]:
    """llms.txtファイルを読み込み、アクション設定を取得"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'llms.txt')
        if not os.path.exists(config_path):
            print(f"⚠️ Actions config file not found at {config_path}")
            return {}
            
        with open(config_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Parse YAML structure
        try:
            actions_config = yaml.safe_load(content)
            if isinstance(actions_config, dict) and 'actions' in actions_config:
                return actions_config
            else:
                print("⚠️ Invalid actions config structure")
                return {}
        except yaml.YAMLError as e:
            print(f"⚠️ YAML parsing error: {e}")
            return {}
    except Exception as e:
        print(f"⚠️ Error loading actions config: {e}")
        return {}

def pre_evaluate_prompt_standalone(prompt: str) -> Optional[Dict[str, Any]]:
    """
    LLM非依存でプロンプトを事前評価し、登録済みアクションとマッチするかチェック
    
    Args:
        prompt: ユーザープロンプト
        
    Returns:
        Optional[Dict[str, Any]]: マッチしたアクション情報またはNone
    """
    try:
        print(f"🔍 Evaluating prompt: {prompt}")
        actions_config = load_actions_config_standalone()
        
        if not actions_config or 'actions' not in actions_config:
            print("⚠️ No actions config available")
            return None
        
        actions = actions_config['actions']
        
        # 最初に正確なマッチを探す
        for action in actions:
            if isinstance(action, dict) and 'name' in action:
                action_name = action['name']
                
                # @コマンド形式の正確なマッチング (例: @phrase-search)
                if prompt.startswith(f"@{action_name}") or f"@{action_name}" in prompt:
                    print(f"✅ Found exact matching action: {action_name}")
                    
                    # パラメータを抽出
                    extracted_params = extract_params_standalone(prompt, action.get('params', []))
                    
                    return {
                        'is_command': True,
                        'command_name': action_name,
                        'action_def': action,
                        'params': extracted_params
                    }
        
        # 次に部分的なマッチを探す
        for action in actions:
            if isinstance(action, dict) and 'name' in action:
                action_name = action['name']
                
                # より柔軟なマッチング（キーワードベース）- ただし、より厳密に
                action_keywords = action_name.split('-')
                prompt_words = prompt.lower().split()
                
                # すべてのキーワードが含まれているかチェック
                if all(keyword in prompt.lower() for keyword in action_keywords):
                    print(f"✅ Found partial matching action: {action_name}")
                    
                    # パラメータを抽出
                    extracted_params = extract_params_standalone(prompt, action.get('params', []))
                    
                    return {
                        'is_command': True,
                        'command_name': action_name,
                        'action_def': action,
                        'params': extracted_params
                    }
        
        print("⚠️ No matching action found")
        return None
        
    except Exception as e:
        print(f"❌ Error in pre_evaluate_prompt_standalone: {str(e)}")
        return None

def extract_params_standalone(prompt: str, param_names: Union[str, List[Dict[str, Any]], None]) -> Dict[str, str]:
    """
    LLM非依存でプロンプトからパラメータを抽出
    
    Args:
        prompt: ユーザープロンプト
        param_names: 抽出するパラメータ名
        
    Returns:
        Dict[str, str]: 抽出されたパラメータ
    """
    print(f"🔍 Extracting parameters from: {prompt}")
    params = {}
    
    if not param_names:
        return params
    
    # Convert param_names to list if it's a string
    if isinstance(param_names, str):
        param_list = [p.strip() for p in param_names.split(',')]
    elif isinstance(param_names, list):
        param_list = [p['name'] for p in param_names if isinstance(p, dict) and 'name' in p]
    else:
        return params

    for param in param_list:
        # パラメータ=値 形式の抽出
        match = re.search(rf'{param}=(\S+)', prompt)
        if match:
            params[param] = match.group(1)
            print(f"✅ Extracted {param}={params[param]}")
        else:
            # スペース区切りでの抽出も試行
            words = prompt.split()
            for i, word in enumerate(words):
                if param in word.lower() and i + 1 < len(words):
                    params[param] = words[i + 1]
                    print(f"✅ Extracted {param}={params[param]} (space-separated)")
                    break

    print(f"🔍 Final extracted params: {params}")
    return params

def resolve_sensitive_env_variables_standalone(text: str) -> str:
    """
    LLM非依存で環境変数を解決
    
    Args:
        text: 解決するテキスト
        
    Returns:
        str: 環境変数が解決されたテキスト
    """
    if not text:
        return text
    
    # 環境変数の置換 (${VAR_NAME} 形式)
    def replace_env_var(match):
        var_name = match.group(1)
        return os.getenv(var_name, match.group(0))
    
    # ${...} 形式の環境変数を置換
    result = re.sub(r'\$\{([^}]+)\}', replace_env_var, text)
    
    return result
