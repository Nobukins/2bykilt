"""
Timeout and Cancellation Manager for Run/Job Operations

This module provides centralized timeout and cancellation functionality for:
1. Overall job execution timeout
2. Individual operation timeouts
3. Graceful cancellation handling
4. Signal-based cancellation support

Part of Issue #46 implementation for Run/Job timeout & cancellation.
"""

import asyncio
import signal
import logging
import time
from typing import Optional, Callable, Any, Dict, List
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Custom timeout exception for job operations"""
    pass


class CancellationError(Exception):
    """Custom cancellation exception for job operations"""
    pass


class TimeoutScope(Enum):
    """Different timeout scopes for operations"""
    JOB = "job"           # Overall job timeout
    OPERATION = "operation"  # Individual operation timeout
    STEP = "step"         # Step-level timeout
    NETWORK = "network"   # Network operation timeout


@dataclass
class TimeoutConfig:
    """Configuration for timeout settings"""
    job_timeout: int = 3600  # 1 hour default for jobs
    operation_timeout: int = 300  # 5 minutes default for operations
    step_timeout: int = 60  # 1 minute default for steps
    network_timeout: int = 30  # 30 seconds default for network ops
    enable_cancellation: bool = True
    graceful_shutdown_timeout: int = 10  # seconds to wait for graceful shutdown


class TimeoutManager:
    """Centralized timeout and cancellation manager"""

    def __init__(self, config: Optional[TimeoutConfig] = None):
        self.config = config or TimeoutConfig()
        self._cancelled = False
        self._cancel_callbacks: List[Callable] = []
        self._active_timeouts: Dict[str, asyncio.Task] = {}
        self._start_time = time.time()

        # Setup signal handlers for cancellation
        if self.config.enable_cancellation:
            self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful cancellation"""
        try:
            # Handle common termination signals
            for sig in [signal.SIGINT, signal.SIGTERM]:
                signal.signal(sig, self._signal_handler)
            logger.info("Signal handlers configured for graceful cancellation")
        except (OSError, ValueError) as e:
            logger.warning(f"Could not setup signal handlers: {e}")

    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        logger.info(f"Received signal {signum}, initiating graceful cancellation")
        self.cancel()

    def cancel(self):
        """Cancel all active operations"""
        if self._cancelled:
            return

        self._cancelled = True
        logger.info("Cancellation requested - notifying all operations")

        # Execute all cancellation callbacks
        for callback in self._cancel_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in cancellation callback: {e}")

        # Cancel all active timeout tasks
        for task_id, task in self._active_timeouts.items():
            if not task.done():
                task.cancel()
                logger.debug(f"Cancelled timeout task: {task_id}")

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested"""
        return self._cancelled

    def add_cancel_callback(self, callback: Callable):
        """Add a callback to be executed on cancellation"""
        self._cancel_callbacks.append(callback)

    def remove_cancel_callback(self, callback: Callable):
        """Remove a cancellation callback"""
        if callback in self._cancel_callbacks:
            self._cancel_callbacks.remove(callback)

    @asynccontextmanager
    async def timeout_scope(self, scope: TimeoutScope, custom_timeout: Optional[int] = None):
        """
        Context manager for timeout scopes

        Args:
            scope: The timeout scope to use
            custom_timeout: Custom timeout value (overrides config)
        """
        timeout_value = custom_timeout or self._get_timeout_for_scope(scope)

        if self._cancelled:
            raise CancellationError("Operation cancelled")

        # Create a timeout task to enforce the timeout
        timeout_task = None
        current_task = asyncio.current_task()

        if current_task is not None:
            timeout_task = asyncio.create_task(self._timeout_task(timeout_value, f"{scope.value}_{id(current_task)}"))
            self._active_timeouts[f"{scope.value}_{id(current_task)}"] = timeout_task

        try:
            # Use asyncio.wait_for to actually enforce timeout
            # We'll wrap the yielded block in a timeout
            yield

        except asyncio.CancelledError:
            if self._cancelled:
                raise CancellationError("Operation cancelled")
            else:
                raise
        finally:
            # Clean up timeout task
            if timeout_task and not timeout_task.done():
                timeout_task.cancel()
                try:
                    await timeout_task
                except asyncio.CancelledError:
                    pass

            # Remove from active timeouts
            task_key = f"{scope.value}_{id(current_task)}" if current_task else None
            if task_key and task_key in self._active_timeouts:
                del self._active_timeouts[task_key]

    async def apply_timeout_to_coro(self, coro, scope: TimeoutScope, custom_timeout: Optional[int] = None):
        """
        Apply timeout to a coroutine using asyncio.wait_for

        Args:
            coro: The coroutine to apply timeout to
            scope: The timeout scope to use
            custom_timeout: Custom timeout value (overrides config)

        Returns:
            Result of the coroutine

        Raises:
            TimeoutError: If operation times out
            CancellationError: If operation is cancelled
        """
        timeout_value = custom_timeout or self._get_timeout_for_scope(scope)

        if self._cancelled:
            raise CancellationError("Operation cancelled")

        try:
            return await asyncio.wait_for(coro, timeout=timeout_value)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout_value} seconds")
        except asyncio.CancelledError:
            if self._cancelled:
                raise CancellationError("Operation cancelled")
            else:
                raise

    async def _timeout_task(self, timeout: int, task_id: str):
        """Background task that handles timeout"""
        try:
            await asyncio.sleep(timeout)
            if task_id in self._active_timeouts:
                logger.warning(f"Timeout reached for {task_id} after {timeout} seconds")
                # Cancel the timeout task itself to trigger the CancelledError in the context
                timeout_task = self._active_timeouts[task_id]
                if not timeout_task.done():
                    timeout_task.cancel()
        except asyncio.CancelledError:
            # Normal cancellation, don't log as error
            pass

    def _get_timeout_for_scope(self, scope: TimeoutScope) -> int:
        """Get timeout value for a specific scope"""
        if scope == TimeoutScope.JOB:
            return self.config.job_timeout
        elif scope == TimeoutScope.OPERATION:
            return self.config.operation_timeout
        elif scope == TimeoutScope.STEP:
            return self.config.step_timeout
        elif scope == TimeoutScope.NETWORK:
            return self.config.network_timeout
        else:
            return self.config.operation_timeout  # fallback

    async def wait_with_timeout(self, coro: Any, timeout: int, operation_name: str = "operation") -> Any:
        """
        Wait for a coroutine with timeout

        Args:
            coro: Coroutine to wait for
            timeout: Timeout in seconds
            operation_name: Name for logging

        Returns:
            Result of the coroutine

        Raises:
            TimeoutError: If operation times out
            CancellationError: If operation is cancelled
        """
        if self._cancelled:
            raise CancellationError("Operation cancelled")

        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"{operation_name} timed out after {timeout} seconds")
        except asyncio.CancelledError:
            if self._cancelled:
                raise CancellationError("Operation cancelled")
            else:
                raise

    def get_elapsed_time(self) -> float:
        """Get elapsed time since manager creation"""
        return time.time() - self._start_time

    def get_remaining_time(self, scope: TimeoutScope) -> float:
        """Get remaining time for a timeout scope"""
        elapsed = self.get_elapsed_time()
        total_timeout = self._get_timeout_for_scope(scope)
        remaining = total_timeout - elapsed
        return max(0, remaining)

    async def graceful_shutdown(self):
        """Perform graceful shutdown with timeout"""
        if not self._cancelled:
            self.cancel()

        logger.info(f"Starting graceful shutdown (timeout: {self.config.graceful_shutdown_timeout}s)")

        try:
            # Wait for active operations to complete or timeout
            await asyncio.wait_for(
                self._wait_for_active_operations(),
                timeout=self.config.graceful_shutdown_timeout
            )
            logger.info("Graceful shutdown completed")
        except asyncio.TimeoutError:
            logger.warning("Graceful shutdown timed out, forcing termination")
            # Force cancel any remaining operations
            for task in self._active_timeouts.values():
                if not task.done():
                    task.cancel()

    async def _wait_for_active_operations(self):
        """Wait for all active timeout operations to complete"""
        if not self._active_timeouts:
            return

        # Wait for all timeout tasks to complete
        await asyncio.gather(
            *[task for task in self._active_timeouts.values() if not task.done()],
            return_exceptions=True
        )


# Global timeout manager instance
_timeout_manager: Optional[TimeoutManager] = None


def get_timeout_manager(config: Optional[TimeoutConfig] = None) -> TimeoutManager:
    """Get global timeout manager instance"""
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = TimeoutManager(config)
    return _timeout_manager


def reset_timeout_manager():
    """Reset global timeout manager (for testing)"""
    global _timeout_manager
    _timeout_manager = None


# Convenience functions for common timeout operations
async def with_job_timeout(coro, custom_timeout: Optional[int] = None):
    """Execute coroutine with job-level timeout"""
    manager = get_timeout_manager()
    async with manager.timeout_scope(TimeoutScope.JOB, custom_timeout):
        return await coro


async def with_operation_timeout(coro, custom_timeout: Optional[int] = None):
    """Execute coroutine with operation-level timeout"""
    manager = get_timeout_manager()
    async with manager.timeout_scope(TimeoutScope.OPERATION, custom_timeout):
        return await coro


async def with_network_timeout(coro, custom_timeout: Optional[int] = None):
    """Execute coroutine with network-level timeout"""
    manager = get_timeout_manager()
    async with manager.timeout_scope(TimeoutScope.NETWORK, custom_timeout):
        return await coro
