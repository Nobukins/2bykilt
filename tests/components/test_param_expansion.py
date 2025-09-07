#!/usr/bin/env python3
import re

# 修正されたパターンでテスト
command_template = 'python ./myscript/unified_action_launcher.py --action nogtips_search --query "${params.query|LLMs.txt}" --slowmo 2500 --countdown 3'
params = {}

# エスケープなしのパターン
param_pattern = r'\$\{params\.([^}|]+)(?:\|([^}]*))?\}'

def replace_param(match):
    param_name = match.group(1)
    default_value = match.group(2) if match.group(2) is not None else ''
    
    if param_name in params and params[param_name]:
        param_value = str(params[param_name])
    else:
        param_value = default_value
    
    if ' ' in param_value or any(c in param_value for c in '!@#$%^&*()'):
        return f'"{param_value}"'
    return param_value

result = re.sub(param_pattern, replace_param, command_template)
print(f'Original: {command_template}')
print(f'Result: {result}')
