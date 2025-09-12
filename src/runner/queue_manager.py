"""
Queue Manager for Concurrent Execution Control

This module provides centralized queue management for controlling concurrent
execution of runs/jobs with configurable concurrency limits.

Part of Issue #47 implementation for parallel execution queue & concurrency limits.
"""

import asyncio
import heapq
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class QueueState(Enum):
    """Queue item states"""
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueItem:
    """Queue item representation"""
    id: str
    name: str
    state: QueueState
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    priority: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def __lt__(self, other: 'QueueItem') -> bool:
        """Compare items by priority (higher priority first)"""
        if self.priority != other.priority:
            return self.priority > other.priority  # Higher priority first
        return self.created_at < other.created_at  # FIFO for same priority


class QueueManager:
    """
    Manages execution queue with concurrency limits

    Features:
    - Configurable max concurrency
    - Queue state tracking
    - Async execution support
    - Thread-safe operations
    """

    def __init__(self, artifacts_dir: Path, max_concurrency: int = 5):
        self.artifacts_dir = artifacts_dir
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._queue: List[QueueItem] = []  # Will use heapq operations
        self._active: Dict[str, QueueItem] = {}
        self._completed: Dict[str, QueueItem] = {}
        self._lock = threading.Lock()
        self._completed_count = 0
        self._cancelled_count = 0
        self._shutdown_event = asyncio.Event()
        self._stats_task: Optional[asyncio.Task] = None

        # Statistics tracking
        self._stats = {
            "total_enqueued": 0,
            "total_completed": 0,
            "total_failed": 0,
            "max_queue_length": 0,
            "avg_wait_time": 0.0
        }

        # Don't start stats logging automatically - let caller start it when ready

    async def start_stats_logging(self) -> None:
        """Start periodic queue statistics logging (async)"""
        if self._stats_task is not None:
            return  # Already started

        async def log_stats_periodically():
            while not self._shutdown_event.is_set():
                try:
                    await asyncio.sleep(30)  # Log stats every 30 seconds
                    if not self._shutdown_event.is_set():
                        self.log_queue_stats()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in periodic stats logging: {e}")

        self._stats_task = asyncio.create_task(log_stats_periodically())

    @property
    def max_concurrency(self) -> int:
        """Get current max concurrency"""
        return self._max_concurrency

    @max_concurrency.setter
    def max_concurrency(self, value: int) -> None:
        """Set max concurrency"""
        if value < 1:
            raise ValueError("Max concurrency must be at least 1")

        # Only allow changing if no active tasks are running
        if not self._has_no_pending_tasks():
            raise RuntimeError("Cannot change max_concurrency while tasks are active.")

        self._max_concurrency = value
        self._semaphore = asyncio.Semaphore(value)

    def _has_no_pending_tasks(self) -> bool:
        """
        Check if there are no active or waiting tasks (pending tasks)

        Returns:
            bool: True if there are no active or waiting tasks, False otherwise
        """
        return len(self._active) == 0 and len(self._queue) == 0

    # Test helper methods
    def _add_active_item_for_testing(self, item_id: str, name: str) -> None:
        """Test helper: Add an active item (violates encapsulation for testing)"""
        item = QueueItem(
            id=item_id,
            name=name,
            state=QueueState.RUNNING,
            created_at=time.time()
        )
        self._active[item_id] = item

    def _clear_queue_for_testing(self) -> None:
        """Test helper: Clear the queue (violates encapsulation for testing)"""
        self._queue.clear()

    def _get_shutdown_event_for_testing(self) -> asyncio.Event:
        """Test helper: Get shutdown event (violates encapsulation for testing)"""
        return self._shutdown_event

    async def shutdown(self) -> None:
        """
        Shutdown the queue manager gracefully
        """
        logger.info("Shutting down QueueManager")

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel stats task
        if self._stats_task and not self._stats_task.done():
            self._stats_task.cancel()
            try:
                await self._stats_task
            except asyncio.CancelledError:
                pass

        # Cancel all waiting items in queue
        with self._lock:
            while self._queue:
                item = heapq.heappop(self._queue)
                item.state = QueueState.CANCELLED
                item.completed_at = time.time()
                self._completed[item.id] = item
                self._cancelled_count += 1
                logger.info(f"Item cancelled during shutdown: {item.id}")

        # Wait for active tasks to complete
        if self._active:
            logger.info(f"Waiting for {len(self._active)} active tasks to complete")
            # Note: In a real implementation, you might want to add timeouts here

        # Log final stats
        self.log_queue_stats()

        logger.info("QueueManager shutdown complete")

    def enqueue(self, item_id: str, name: str, priority: int = 0, metadata: Dict[str, Any] = None) -> QueueItem:
        """
        Add item to execution queue

        Args:
            item_id: Unique identifier for the item
            name: Human-readable name
            priority: Priority (higher = more important)
            metadata: Additional metadata

        Returns:
            QueueItem: The created queue item
        """
        with self._lock:
            # Check if item already exists
            if item_id in self._active or item_id in [item.id for item in self._queue]:
                raise ValueError(f"Item {item_id} already exists in queue")

            item = QueueItem(
                id=item_id,
                name=name,
                state=QueueState.WAITING,
                created_at=time.time(),
                priority=priority,
                metadata=metadata or {}
            )

            # Add to priority queue
            heapq.heappush(self._queue, item)
            self._stats["total_enqueued"] += 1
            self._stats["max_queue_length"] = max(self._stats["max_queue_length"], len(self._queue))

            logger.info(f"Item enqueued: {item_id} (priority={priority}, queue_length={len(self._queue)})")

            # Log to queue log
            self._log_queue_event("enqueued", item)

            return item

    async def execute_next(self) -> Optional[QueueItem]:
        """
        Execute next item in queue (async)

        Returns:
            QueueItem or None: Next item to execute, or None if queue empty
        """
        async with self._semaphore:
            with self._lock:
                if not self._queue:
                    return None

                item = heapq.heappop(self._queue)
                item.state = QueueState.RUNNING
                item.started_at = time.time()
                self._active[item.id] = item

                logger.info(f"Item started: {item.id} (running={len(self._active)})")

                # Log to queue log
                self._log_queue_event("started", item)

                return item

    def complete_item(self, item_id: str, success: bool = True) -> None:
        """
        Mark item as completed

        Args:
            item_id: Item identifier
            success: Whether execution was successful
        """
        with self._lock:
            if item_id not in self._active:
                logger.warning(f"Item {item_id} not found in running items")
                return

            item = self._active.pop(item_id)
            item.state = QueueState.COMPLETED if success else QueueState.FAILED
            item.completed_at = time.time()
            self._completed[item_id] = item

            if success:
                self._stats["total_completed"] += 1
                self._completed_count += 1
            else:
                self._stats["total_failed"] += 1

            # Calculate wait time
            if item.started_at and item.created_at:
                wait_time = item.started_at - item.created_at
                # Update rolling average
                total_completed = self._stats["total_completed"] + self._stats["total_failed"]
                if total_completed > 0:
                    self._stats["avg_wait_time"] = (
                        (self._stats["avg_wait_time"] * (total_completed - 1)) + wait_time
                    ) / total_completed

            logger.info(f"Item completed: {item_id} (success={success})")

            # Log to queue log
            self._log_queue_event("completed", item)

    def cancel_item(self, item_id: str) -> None:
        """
        Cancel running item

        Args:
            item_id: Item identifier
        """
        with self._lock:
            if item_id not in self._active:
                logger.warning(f"Item {item_id} not found in running items")
                return

            item = self._active.pop(item_id)
            item.state = QueueState.CANCELLED
            item.completed_at = time.time()
            self._completed[item_id] = item
            self._cancelled_count += 1

            logger.info(f"Item cancelled: {item_id}")

            # Log to queue log
            self._log_queue_event("cancelled", item)

    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status

        Returns:
            Dict with queue statistics and current state
        """
        with self._lock:
            return {
                "queue_length": len(self._queue),
                "running_count": len(self._active),
                "completed_count": len(self._completed),
                "max_concurrency": self.max_concurrency,
                "current_concurrency": len(self._active),
                "stats": self._stats.copy(),
                "waiting_items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "priority": item.priority,
                        "wait_time": time.time() - item.created_at
                    }
                    for item in sorted(self._queue, key=lambda x: (-x.priority, x.created_at))
                ],
                "running_items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "run_time": time.time() - (item.started_at or time.time())
                    }
                    for item in self._active.values()
                ]
            }

    def _log_queue_event(self, event: str, item: QueueItem) -> None:
        """
        Log queue event to file

        Args:
            event: Event type (enqueued, started, completed, cancelled)
            item: Queue item
        """
        try:
            log_file = self.artifacts_dir / "runs" / item.id / "queue.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            log_entry = f"[{timestamp}] {event.upper()}: {item.id} ({item.name}) priority={item.priority}"

            if item.started_at and item.created_at:
                wait_time = item.started_at - item.created_at
                log_entry += f" wait_time={wait_time:.2f}s"

            if item.completed_at and item.started_at:
                run_time = item.completed_at - item.started_at
                log_entry += f" run_time={run_time:.2f}s"

            log_entry += "\n"

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)

            # Update manifest with queue state
            self._update_manifest_queue_state(item, event)

        except Exception as e:
            logger.error(f"Failed to log queue event: {e}")

    def _update_manifest_queue_state(self, item: QueueItem, event: str) -> None:
        """
        Update manifest with queue state change

        Args:
            item: Queue item
            event: Event type (enqueued, started, completed, cancelled)
        """
        try:
            from src.core.artifact_manager import get_artifact_manager
            artifact_manager = get_artifact_manager()

            manifest = artifact_manager.get_manifest()

            # Initialize queue_state if not exists
            if "queue_state" not in manifest:
                manifest["queue_state"] = {
                    "items": {},
                    "events": []
                }

            # Update item state
            queue_state = manifest["queue_state"]
            queue_state["items"][item.id] = {
                "name": item.name,
                "state": item.state.value,
                "created_at": item.created_at,
                "started_at": item.started_at,
                "completed_at": item.completed_at,
                "priority": item.priority,
                "metadata": item.metadata
            }

            # Add event to events list
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            event_entry = {
                "timestamp": timestamp,
                "event": event,
                "item_id": item.id,
                "item_name": item.name,
                "state": item.state.value
            }
            queue_state["events"].append(event_entry)

            # Keep only last 1000 events to prevent manifest from growing too large
            if len(queue_state["events"]) > 1000:
                queue_state["events"] = queue_state["events"][-1000:]

            artifact_manager.persist_manifest()

        except Exception as e:
            logger.error(f"Failed to update manifest queue state: {e}")

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get current queue statistics

        Returns:
            Dictionary with queue statistics
        """
        with self._lock:
            now = time.time()
            stats = {
                "total_items": len(self._queue),
                "active_items": len(self._active),
                "completed_items": self._completed_count,
                "cancelled_items": self._cancelled_count,
                "max_concurrency": self._max_concurrency,
                "current_concurrency": len(self._active),
                "queue_depth": len(self._queue),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
            }

            # Calculate average wait times
            if self._completed_count > 0:
                completed_items = list(self._completed.values())

                # Calculate average wait time using only items with valid timestamps
                wait_items = [
                    item for item in completed_items
                    if item.started_at and item.created_at
                ]
                if wait_items:
                    total_wait = sum(
                        item.started_at - item.created_at
                        for item in wait_items
                    )
                    stats["avg_wait_time"] = total_wait / len(wait_items)
                else:
                    stats["avg_wait_time"] = 0

                # Calculate average run time using only items with valid timestamps
                run_items = [
                    item for item in completed_items
                    if item.completed_at and item.started_at
                ]
                if run_items:
                    total_run = sum(
                        item.completed_at - item.started_at
                        for item in run_items
                    )
                    stats["avg_run_time"] = total_run / len(run_items)
                else:
                    stats["avg_run_time"] = 0

            return stats

    def log_queue_stats(self) -> None:
        """
        Log current queue statistics to manifest
        """
        try:
            stats = self.get_queue_stats()

            # Update manifest with queue stats
            from src.core.artifact_manager import get_artifact_manager
            artifact_manager = get_artifact_manager()

            manifest = artifact_manager.get_manifest()

            if "queue_stats" not in manifest:
                manifest["queue_stats"] = []

            # Keep only last 100 stats entries to prevent manifest from growing too large
            queue_stats = manifest["queue_stats"]
            queue_stats.append(stats)
            if len(queue_stats) > 100:
                queue_stats.pop(0)

            artifact_manager.persist_manifest()

            logger.info("Queue stats logged", extra={"queue_stats": stats})

        except Exception as e:
            logger.error(f"Failed to log queue stats: {e}")

    def update_max_concurrency(self, new_limit: int) -> None:
        """
        Update maximum concurrency limit

        Args:
            new_limit: New concurrency limit
        """
        if new_limit < 1:
            raise ValueError("Max concurrency must be at least 1")

        # Only allow changing if no active tasks are running
        if not self._has_no_pending_tasks():
            raise RuntimeError("Cannot change max_concurrency while tasks are active.")

        old_limit = self._max_concurrency
        self._max_concurrency = new_limit
        self._semaphore = asyncio.Semaphore(new_limit)

        logger.info(f"Max concurrency updated: {old_limit} -> {new_limit}")


# Global queue manager instance
_queue_manager: Optional[QueueManager] = None


def get_queue_manager(max_concurrency: Optional[int] = None) -> QueueManager:
    """
    Get global queue manager instance

    Args:
        max_concurrency: Max concurrency for new instance

    Returns:
        QueueManager: Global queue manager instance
    """
    global _queue_manager
    if _queue_manager is None:
        # Try to load from config if not specified
        if max_concurrency is None:
            try:
                from src.config.multi_env_loader import load_config
                config = load_config()
                max_concurrency = config.get("runner", {}).get("max_concurrency", 3)
            except Exception as e:
                logger.warning(f"Failed to load max_concurrency from config: {e}, using default=3")
                max_concurrency = 3

        # Get artifacts directory
        from src.runtime.run_context import RunContext
        rc = RunContext.get()
        artifacts_dir = rc.artifact_dir("art")

        _queue_manager = QueueManager(artifacts_dir=artifacts_dir, max_concurrency=max_concurrency or 3)
    return _queue_manager


def reset_queue_manager():
    """Reset global queue manager (for testing)"""
    global _queue_manager
    _queue_manager = None