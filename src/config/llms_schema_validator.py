"""llms.txt Schema & Validator (Issue #63)

Minimal in-process schema validation for the `llms.txt` actions file.

Design goals (v1 / Issue #63 scope):
  * Zero external dependencies (use PyYAML already present).
  * Fail-fast structural validation (raise LLMSSchemaValidationError) when
    strict mode requested; otherwise collect & return errors.
  * Backward-compatible: Unknown optional fields are ignored (future‑proof).
  * Duplicate action name detection.
  * Action type specific required field checks.

Non-goals (future issues):
  * Advanced param typing / enum / pattern validation
  * Flow step deep semantic validation (only structural keys checked now)
  * Version negotiation (schema_version reserved for future)

Public API:
  validate_llms_content(text: str, *, strict: bool = False) -> dict
    Returns parsed YAML root (possibly with collected warnings) or raises.

  validate_llms_actions(data: dict, *, strict: bool = False) -> list[dict]
    Validates already-parsed data structure.

Artifact / logging integration intentionally omitted for minimal footprint.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import yaml

from src.utils.app_logger import logger

ALLOWED_ACTION_TYPES = {"script", "browser-control", "git-script", "unlock-future"}
FLOW_REQUIRED_KEY_PER_ACTION = {
    # Minimum structural expectations; extended semantics later
    "browser-control": {"flow"},
    "unlock-future": set(),  # flow optional for unlock-future for now
    "script": set(),  # command OR script field (validated separately)
    "git-script": {"git", "script_path"},
}


class LLMSSchemaValidationError(Exception):
    """Raised when llms.txt content is structurally invalid (strict mode)."""


@dataclass(slots=True)
class ValidationIssue:
    level: str  # "error" | "warning"
    path: str
    message: str


def _err(issues: List[ValidationIssue], path: str, msg: str) -> None:
    issues.append(ValidationIssue("error", path, msg))


def _warn(issues: List[ValidationIssue], path: str, msg: str) -> None:
    issues.append(ValidationIssue("warning", path, msg))


def validate_llms_content(text: str, *, strict: bool = False) -> Dict[str, Any]:
    """Parse & validate raw llms.txt YAML content.

    Returns the parsed root dict (even if errors in non-strict mode) and logs
    validation issues. Raises LLMSSchemaValidationError if strict and errors.
    """
    try:
        data = yaml.safe_load(text) or {}
    except Exception as e:  # noqa: BLE001
        raise LLMSSchemaValidationError(f"YAML parse failure: {e}") from e
    validate_llms_actions(data, strict=strict)  # will raise if strict & errors
    return data


def validate_llms_actions(data: Dict[str, Any], *, strict: bool = False) -> List[Dict[str, Any]]:
    """Validate already parsed llms.txt root mapping.

    Returns the list of valid action dicts (may exclude invalid ones when
    non-strict). In non-strict mode, invalid actions are skipped but errors
    are logged. Strict mode raises on any error.
    """
    issues: List[ValidationIssue] = []
    root_path = "root"
    if not isinstance(data, dict):
        raise LLMSSchemaValidationError("Top-level YAML must be a mapping containing 'actions'.")
    actions_raw = data.get("actions")
    if not isinstance(actions_raw, list):
        _err(issues, "actions", "Missing or non-list 'actions' key")
    else:
        validated: List[Dict[str, Any]] = []
        seen_names = set()
        for idx, action in enumerate(actions_raw):
            path_prefix = f"actions[{idx}]"
            if not isinstance(action, dict):
                _err(issues, path_prefix, "Action entry must be a mapping")
                continue
            name = action.get("name")
            if not isinstance(name, str) or not name.strip():
                _err(issues, f"{path_prefix}.name", "Action 'name' required (non-empty string)")
                continue  # can't proceed without name
            if name in seen_names:
                _err(issues, f"{path_prefix}.name", f"Duplicate action name '{name}'")
                continue
            seen_names.add(name)
            a_type = action.get("type")
            if not isinstance(a_type, str) or a_type not in ALLOWED_ACTION_TYPES:
                _err(issues, f"{path_prefix}.type", f"Invalid or missing action 'type' (allowed: {sorted(ALLOWED_ACTION_TYPES)})")
            # Type-specific required keys
            for required_key in FLOW_REQUIRED_KEY_PER_ACTION.get(a_type, set()):
                if required_key not in action:
                    _err(issues, f"{path_prefix}.{required_key}", f"Missing required field '{required_key}' for type '{a_type}'")
            # script/git-script nuance
            if a_type == "script":
                if not any(k in action for k in ("command", "script")):
                    _err(issues, f"{path_prefix}", "script action requires 'command' or 'script'")
            if a_type == "git-script":
                for k in ("git", "script_path"):
                    if k not in action or not action.get(k):  # robustness
                        _err(issues, f"{path_prefix}.{k}", f"git-script action missing '{k}'")
            # params validation (basic)
            params = action.get("params")
            if params is not None:
                if not isinstance(params, list):
                    _err(issues, f"{path_prefix}.params", "'params' must be a list if provided")
                else:
                    seen_param_names: set[str] = set()
                    for p_idx, p in enumerate(params):
                        p_path = f"{path_prefix}.params[{p_idx}]"
                        if not isinstance(p, dict):
                            _err(issues, p_path, "param must be a mapping")
                            continue
                        p_name = p.get("name")
                        if not isinstance(p_name, str) or not p_name:
                            _err(issues, f"{p_path}.name", "param 'name' required")
                            continue
                        if p_name in seen_param_names:
                            _err(issues, f"{p_path}.name", f"Duplicate param name '{p_name}' in action '{name}'")
                        seen_param_names.add(p_name)
                        # required flag
                        if "required" in p and not isinstance(p.get("required"), bool):
                            _err(issues, f"{p_path}.required", "'required' must be boolean if present")
            # flow validation basic
            flow = action.get("flow")
            if flow is not None:
                if not isinstance(flow, list):
                    _err(issues, f"{path_prefix}.flow", "'flow' must be a list if provided")
                else:
                    for s_idx, step in enumerate(flow):
                        s_path = f"{path_prefix}.flow[{s_idx}]"
                        if not isinstance(step, dict):
                            _err(issues, s_path, "flow step must be a mapping")
                            continue
                        if "action" not in step:
                            _err(issues, s_path, "flow step missing 'action'")
            # Collect valid if no action-specific errors (warnings none defined yet)
            # Determine if this action had errors:
            action_had_error = any(i for i in issues if i.level == "error" and i.path.startswith(path_prefix))
            if not action_had_error:
                validated.append(action)
        # Final duplicate global id check already done via set
    # Decide outcome
    error_count = sum(1 for i in issues if i.level == "error")
    warning_count = sum(1 for i in issues if i.level == "warning")
    if error_count:
        for issue in issues:
            log_fn = logger.error if issue.level == "error" else logger.warning
            log_fn(f"llms.txt validation {issue.level}: {issue.path}: {issue.message}")
        if strict:
            raise LLMSSchemaValidationError(f"llms.txt validation failed: {error_count} errors, {warning_count} warnings")
    else:
        for issue in issues:  # currently only warnings path
            logger.warning(f"llms.txt validation warning: {issue.path}: {issue.message}")
    # On non-strict error scenario we return only valid actions (skip invalid)
    return data.get("actions", []) if not error_count else [a for a in data.get("actions", []) if isinstance(a, dict) and a.get("name")]


__all__ = [
    "validate_llms_content",
    "validate_llms_actions",
    "LLMSSchemaValidationError",
]
