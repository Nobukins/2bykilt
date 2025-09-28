import os
import pickle
import uuid
import json
import jsonschema
import gradio as gr

# Try to import multi-environment configuration support
try:
    from ..config.config_adapter import get_config_for_environment, is_multi_env_config_available
    MULTI_ENV_AVAILABLE = is_multi_env_config_available()
except ImportError:
    MULTI_ENV_AVAILABLE = False

# Import unified recording directory resolver
try:
    from .recording_dir_resolver import create_or_get_recording_dir
except ImportError:
    # Fallback if resolver is not available
    from pathlib import Path
    def create_or_get_recording_dir():
        return Path("./tmp/record_videos").resolve()

# Import Feature Flags for security controls
try:
    from ..config.feature_flags import FeatureFlags
    FEATURE_FLAGS_AVAILABLE = True
except ImportError:
    FEATURE_FLAGS_AVAILABLE = False


def default_config():
    """Prepare the default configuration"""
    # Try to use multi-environment configuration first
    if MULTI_ENV_AVAILABLE:
        try:
            config = get_config_for_environment()
            return config
        except Exception as e:
            print(f"Warning: Failed to load multi-env config: {e}")
            print("Falling back to legacy configuration")
    
    # Fallback to legacy default configuration
    return {
        "agent_type": "custom",
        "max_steps": 100,
        "max_actions_per_step": 10,
        "use_vision": True,
        "tool_calling_method": "auto",
        "llm_provider": "openai",
        "llm_model_name": "gpt-4o",
        "llm_num_ctx": 32000,
        "llm_temperature": 1.0,
        "llm_base_url": "",
        "llm_api_key": "",
        "use_own_browser": os.getenv("CHROME_PERSISTENT_SESSION", "false").lower() == "true",
        "keep_browser_open": False,
        "headless": False,
        "disable_security": True,
        "enable_recording": True,
        "window_w": 1280,
        "window_h": 1100,
        "save_recording_path": str(create_or_get_recording_dir()),
        "save_trace_path": "./tmp/traces",
        "save_agent_history_path": "./tmp/agent_history",
        "task": "script-nogtips query=Personal_AI_Assistant",
        "dev_mode": False,  # Add dev mode setting
    }


# JSON Schema for configuration validation
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "agent_type": {"type": "string"},
        "max_steps": {"type": "integer", "minimum": 1},
        "max_actions_per_step": {"type": "integer", "minimum": 1},
        "use_vision": {"type": "boolean"},
        "tool_calling_method": {"type": "string"},
        "llm_provider": {"type": "string"},
        "llm_model_name": {"type": "string"},
        "llm_num_ctx": {"type": "integer", "minimum": 1},
        "llm_temperature": {"type": "number", "minimum": 0, "maximum": 2},
        "llm_base_url": {"type": "string"},
        "llm_api_key": {"type": "string"},
        "use_own_browser": {"type": "boolean"},
        "keep_browser_open": {"type": "boolean"},
        "headless": {"type": "boolean"},
        "disable_security": {"type": "boolean"},
        "enable_recording": {"type": "boolean"},
        "window_w": {"type": "integer", "minimum": 1},
        "window_h": {"type": "integer", "minimum": 1},
        "save_recording_path": {"type": "string"},
        "save_trace_path": {"type": "string"},
        "save_agent_history_path": {"type": "string"},
        "task": {"type": "string"},
        "dev_mode": {"type": "boolean"},
    },
    "required": ["agent_type", "max_steps", "max_actions_per_step", "use_vision", "tool_calling_method", "llm_provider", "llm_model_name", "llm_num_ctx", "llm_temperature", "llm_base_url", "llm_api_key", "use_own_browser", "keep_browser_open", "headless", "disable_security", "enable_recording", "window_w", "window_h", "save_recording_path", "save_trace_path", "save_agent_history_path", "task", "dev_mode"]
}


def load_config_from_file(config_file):
    """Load settings from a UUID.pkl file."""
    try:
        with open(config_file, 'rb') as f:
            settings = pickle.load(f)
        return settings
    except Exception as e:
        return f"Error loading configuration: {str(e)}"


def load_config_from_json(config_file):
    """Load settings from a JSON file with schema validation."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        jsonschema.validate(instance=settings, schema=CONFIG_SCHEMA)
        return settings
    except jsonschema.ValidationError as e:
        return f"Error validating configuration: {str(e)}"
    except Exception as e:
        return f"Error loading configuration: {str(e)}"


def save_config_to_file(settings, save_dir="./tmp/webui_settings"):
    """Save the current settings to a UUID.pkl file with a UUID name."""
    os.makedirs(save_dir, exist_ok=True)
    config_file = os.path.join(save_dir, f"{uuid.uuid4()}.pkl")
    with open(config_file, 'wb') as f:
        pickle.dump(settings, f)
    return f"Configuration saved to {config_file}"


def save_config_to_json(settings, save_dir="./tmp/webui_settings"):
    """Save the current settings to a config.json file."""
    os.makedirs(save_dir, exist_ok=True)
    config_file = os.path.join(save_dir, "config.json")
    try:
        jsonschema.validate(instance=settings, schema=CONFIG_SCHEMA)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return f"Configuration saved to {config_file}"
    except jsonschema.ValidationError as e:
        return f"Error validating configuration: {str(e)}"
    except Exception as e:
        return f"Error saving configuration: {str(e)}"


def save_current_config(*args):
    current_config = {
        "agent_type": args[0],
        "max_steps": args[1],
        "max_actions_per_step": args[2],
        "use_vision": args[3],
        "tool_calling_method": args[4],
        "llm_provider": args[5],
        "llm_model_name": args[6],
        "llm_num_ctx": args[7],
        "llm_temperature": args[8],
        "llm_base_url": args[9],
        "llm_api_key": args[10],
        "use_own_browser": args[11],
        "keep_browser_open": args[12],
        "headless": args[13],
        "disable_security": args[14],
        "enable_recording": args[15],
        "window_w": args[16],
        "window_h": args[17],
        "save_recording_path": args[18],
        "save_trace_path": args[19],
        "save_agent_history_path": args[20],
        "task": args[21],
        "dev_mode": args[22],
    }
    return save_config_to_file(current_config)


def update_ui_from_config(config_file):
    if config_file is not None:
        # Security check: Reject .pkl files to prevent deserialization of untrusted data
        if config_file.name.endswith('.pkl'):
            # Use Feature Flag for security control (fallback to env var if flags unavailable)
            if FEATURE_FLAGS_AVAILABLE:
                allow_pickle = FeatureFlags.is_enabled("security.allow_pickle_config")
            else:
                allow_pickle = os.getenv('ALLOW_PICKLE_CONFIG', 'false').lower() == 'true'
            
            if not allow_pickle:
                return (
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), "Error: .pkl files are not allowed for security reasons. Please use JSON format."
                )
            loaded_config = load_config_from_file(config_file.name)
        elif config_file.name.endswith('.json'):
            loaded_config = load_config_from_json(config_file.name)
        else:
            return (
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), "Error: Only .json files are supported. .pkl files are disabled for security."
            )
        if isinstance(loaded_config, dict):
            return (
                gr.update(value=loaded_config.get("agent_type", "custom")),
                gr.update(value=loaded_config.get("max_steps", 100)),
                gr.update(value=loaded_config.get("max_actions_per_step", 10)),
                gr.update(value=loaded_config.get("use_vision", True)),
                gr.update(value=loaded_config.get("tool_calling_method", True)),
                gr.update(value=loaded_config.get("llm_provider", "openai")),
                gr.update(value=loaded_config.get("llm_model_name", "gpt-4o")),
                gr.update(value=loaded_config.get("llm_num_ctx", 32000)),
                gr.update(value=loaded_config.get("llm_temperature", 1.0)),
                gr.update(value=loaded_config.get("llm_base_url", "")),
                gr.update(value=loaded_config.get("llm_api_key", "")),
                gr.update(value=loaded_config.get("use_own_browser", False)),
                gr.update(value=loaded_config.get("keep_browser_open", False)),
                gr.update(value=loaded_config.get("headless", False)),
                gr.update(value=loaded_config.get("disable_security", True)),
                gr.update(value=loaded_config.get("enable_recording", True)),
                gr.update(value=loaded_config.get("window_w", 1280)),
                gr.update(value=loaded_config.get("window_h", 1100)),
                gr.update(value=loaded_config.get("save_recording_path", str(create_or_get_recording_dir()))),
                gr.update(value=loaded_config.get("save_trace_path", "./tmp/traces")),
                gr.update(value=loaded_config.get("save_agent_history_path", "./tmp/agent_history")),
                gr.update(value=loaded_config.get("task", "")),
                gr.update(value=loaded_config.get("dev_mode", False)),
                "Configuration loaded successfully."
            )
        else:
            return (
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), "Error: Invalid configuration file."
            )
    return (
        gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
        gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
        gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
        gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
        gr.update(), gr.update(), "No file selected."
    )
