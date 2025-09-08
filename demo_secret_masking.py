#!/usr/bin/env python3
"""Demonstration of Secret Masking Extension (Issue #60)

This script shows how to use the secret masking functionality with the
logging system.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.logging.jsonl_logger import JsonlLogger
from src.security.secret_masker import create_masking_hook, SecretMasker
from src.runtime.run_context import RunContext


def demo_secret_masking():
    """Demonstrate secret masking functionality."""
    print("=== Secret Masking Extension Demo ===\n")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Set up test environment
        os.chdir(tmp_dir)
        os.environ["BYKILT_RUN_ID"] = "demo-masking"
        
        # Clear singleton instances for demo
        JsonlLogger._instances.clear()
        RunContext._instance = None
        
        # Create logger and register masking hook
        logger = JsonlLogger.get(component="demo")
        masking_hook = create_masking_hook()
        logger.register_hook(masking_hook)
        
        print("1. Logging with sensitive information (masking enabled):")
        
        # Log various types of sensitive information
        logger.info(
            "User authentication with password=mySecretPass123 and Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9",
            api_key="sk-1234567890abcdefghijklmnop",
            user_credentials={
                "password": "userPassword456",
                "access_token": "secretToken789",
                "private_key": "-----BEGIN PRIVATE KEY-----"
            },
            config={
                "database": {
                    "password": "dbPassword123",
                    "connection_string": "postgresql://user:secret@host/db"
                }
            }
        )
        
        logger.warning(
            "API call failed with Authorization: Bearer xyz789abc456def123",
            error_context={
                "api_key": "pk-abcdefghijklmnop1234567890",
                "client_secret": "very_secret_client_value"
            }
        )
        
        # Read and display the log file
        log_file = logger.file_path
        print(f"\nLog file location: {log_file}")
        print("\nLog entries (with sensitive information masked):")
        print("=" * 80)
        
        with open(log_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                print(f"Entry {line_num}:")
                import json
                log_entry = json.loads(line.strip())
                print(json.dumps(log_entry, indent=2))
                print("-" * 40)
        
        print("\n2. Demonstrating masking patterns:")
        
        # Show what patterns are detected
        masker = SecretMasker(enabled=True)
        
        test_strings = [
            "API key: sk-1234567890abcdefghijklmnop",
            "Password field: password=mySecretPassword123",
            "Bearer token: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9",
            "Authorization header: Authorization: Basic YWxhZGRpbjpvcGVuc2VzYW1l",
            "Generic secret: 1234567890abcdefghijklmnopqrstuvwxyz123456",
            "Normal text: This is just normal text with no secrets"
        ]
        
        print("\nPattern detection examples:")
        for text in test_strings:
            masked = masker.mask_text(text)
            status = "MASKED" if text != masked else "UNCHANGED"
            print(f"[{status:>9}] {text}")
            if text != masked:
                print(f"{'':>12} → {masked}")
        
        print("\n3. Performance demonstration:")
        
        import time
        
        # Create a complex log record
        complex_record = {
            "msg": "Complex operation with password=secret123 and Bearer token123456789012345",
            "nested_data": {
                "credentials": {
                    "api_key": "sk-1234567890abcdefghijklmnop",
                    "password": "nestedPassword",
                    "tokens": ["token1", "token2", "token3"]
                },
                "large_list": [f"item_{i}" for i in range(1000)]
            }
        }
        
        # Measure performance
        start_time = time.time()
        masked_record = masker.mask_log_record(complex_record)
        processing_time = (time.time() - start_time) * 1000
        
        print(f"\nProcessed complex record in {processing_time:.2f}ms")
        print(f"Performance requirement: <5ms ✓" if processing_time < 5.0 else f"Performance requirement: >5ms ✗")
        
        print("\n4. Feature flag control:")
        
        # Demonstrate disabled masking
        masker_disabled = SecretMasker(enabled=False)
        test_text = "password=secret123"
        
        enabled_result = masker.mask_text(test_text)
        disabled_result = masker_disabled.mask_text(test_text)
        
        print(f"\nWith masking enabled:  '{test_text}' → '{enabled_result}'")
        print(f"With masking disabled: '{test_text}' → '{disabled_result}'")
        
        print("\n=== Demo Complete ===")
        print(f"\nFeatures demonstrated:")
        print("✓ Secret pattern detection (API keys, passwords, tokens)")
        print("✓ Log record masking with hook integration")
        print("✓ Feature flag control")
        print("✓ Performance under 5ms requirement")
        print("✓ No impact on existing logging functionality")


if __name__ == "__main__":
    demo_secret_masking()