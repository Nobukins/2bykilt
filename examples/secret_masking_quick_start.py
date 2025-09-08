"""Quick start guide for integrating secret masking into existing logging."""

from src.logging.jsonl_logger import JsonlLogger
from src.security.secret_masker import create_masking_hook

# For new components or existing components that want secret masking:

def setup_logger_with_masking(component_name: str) -> JsonlLogger:
    """Set up a logger with secret masking enabled.
    
    Args:
        component_name: Name of the component (e.g., 'auth', 'api', 'database')
        
    Returns:
        Configured JsonlLogger with secret masking hook registered
    """
    logger = JsonlLogger.get(component=component_name)
    
    # Register the secret masking hook
    masking_hook = create_masking_hook()
    logger.register_hook(masking_hook)
    
    return logger

# Example usage:
if __name__ == "__main__":
    # Set up logger
    logger = setup_logger_with_masking("example")
    
    # Use normally - sensitive information will be automatically masked
    logger.info(
        "User login attempt with password=secretpass",
        api_key="sk-1234567890abcdefghijklmnop",
        user_data={
            "password": "actual_password",
            "token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9"
        }
    )
    
    logger.warning(
        "API call failed with Authorization: Bearer xyz123abc456",
        error_details={
            "client_secret": "very_secret_value",
            "response_code": 401
        }
    )
    
    print(f"Logs written to: {logger.file_path}")
    print("Check the log file to see masked sensitive information!")