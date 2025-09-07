#!/usr/bin/env python3
"""
Test script for git_script functionality
"""
import sys
import os

def main():
    print("git_script: start")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script arguments: {sys.argv}")
    
    # Check if we have parameters
    if len(sys.argv) > 1:
        query = sys.argv[1] if len(sys.argv) > 1 else "default"
        print(f"Query parameter: {query}")
    else:
        print("No parameters provided")
    
    print("Test script executed successfully")
    print("git_script: end")
    return 0

if __name__ == "__main__":
    sys.exit(main())
