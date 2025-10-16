"""
Process Execution Helpers

This module contains helper functions for subprocess execution.
Extracted from script_manager.py as part of Issue #329 refactoring (Phase 2).
"""

import os
import asyncio
from typing import Optional, List, Tuple
from src.utils.app_logger import logger


async def log_subprocess_output(process):
    """
    Capture and log subprocess output in real-time
    
    Args:
        process: The subprocess to capture output from
    """
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        line_str = line.decode('utf-8').strip()
        if line_str:
            logger.info(f"SUBPROCESS: {line_str}")


async def process_execution(
    command_parts: List[str],
    env: Optional[dict] = None,
    cwd: Optional[str] = None
) -> Tuple[asyncio.subprocess.Process, List[str]]:
    """
    Execute a subprocess command asynchronously with real-time output capture.
    
    Args:
        command_parts: Command to execute as a list of string parts
        env: Environment variables for the subprocess (optional)
        cwd: Working directory for the subprocess (optional)
        
    Returns:
        tuple: (process, output_lines) - The subprocess object and captured output lines
    """
    if env is None:
        env = os.environ.copy()
    
    logger.info(f"Executing command: {' '.join(command_parts)}")
    
    process = await asyncio.create_subprocess_exec(
        *command_parts,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=cwd
    )
    
    output_lines = []
    
    # Stream output in real-time
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        line_str = line.decode('utf-8').strip()
        if line_str:
            logger.info(f"EXEC: {line_str}")
            output_lines.append(line_str)
    
    # Wait for process to complete
    await process.wait()
    
    return process, output_lines
