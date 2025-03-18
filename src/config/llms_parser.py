import re
import os
import logging
import yaml
import requests
from typing import Dict, List, Any, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

def fetch_llms_txt(prompt: str) -> str:
    """
    Fetch llms.txt content either from URL in prompt or local file
    
    Args:
        prompt: User prompt that may contain a URL to llms.txt
        
    Returns:
        str: The content of llms.txt
        
    Raises:
        FileNotFoundError: If llms.txt is not found locally and no URL provided
    """
    url_match = re.search(r'https?://[^\s]+/llms.txt', prompt)
    if url_match:
        url = url_match.group(0)
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    elif os.path.exists('llms.txt'):
        with open('llms.txt', 'r') as file:
            return file.read()
    else:
        raise FileNotFoundError("llms.txt not found locally and no URL provided in prompt.")

def parse_llms_txt(content: str) -> List[Dict[str, Any]]:
    """
    Parse llms.txt content into a list of action dictionaries
    
    Args:
        content: Content of llms.txt
        
    Returns:
        List[Dict[str, Any]]: List of action dictionaries
    """
    data = yaml.safe_load(content)
    return data['actions']

def pre_evaluate_prompt(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Check if prompt matches any action in llms.txt
    
    Args:
        prompt: User prompt
        
    Returns:
        Optional[Dict[str, Any]]: Matched action or None
    """
    try:
        content = fetch_llms_txt(prompt)
        actions = parse_llms_txt(content)
        for action in actions:
            if isinstance(action, dict) and 'name' in action and action['name'] in prompt:
                print(f"Found matching action: {action['name']}")
                return action
        return None
    except Exception as e:
        print(f"pre_evaluate_prompt error: {str(e)}")
        return None

def extract_params(prompt: str, param_names: Union[str, List[Dict[str, Any]], None]) -> Dict[str, str]:
    """
    Extract parameters from prompt based on parameter names
    
    Args:
        prompt: User prompt
        param_names: Parameter names to extract (string, list of dicts, or None)
        
    Returns:
        Dict[str, str]: Extracted parameters
    """
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
        match = re.search(rf'{param}=(\S+)', prompt)
        if match:
            params[param] = match.group(1)
    return params

def resolve_sensitive_env_variables(text: Optional[str]) -> Optional[str]:
    """
    Replace environment variable placeholders with their values
    
    Args:
        text: Text containing environment variable placeholders ($SENSITIVE_*)
        
    Returns:
        Optional[str]: Text with environment variables resolved
    """
    if not text:
        return text
        
    env_vars = re.findall(r'\$SENSITIVE_[A-Za-z0-9_]*', text)
    result = text
    for var in env_vars:
        env_name = var[1:]
        env_value = os.getenv(env_name)
        if env_value is not None:
            result = result.replace(var, env_value)
    return result
