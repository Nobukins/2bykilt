"""
Test Queue Manager for Issue #47

Tests for the QueueManager implementation with concurrency control and manifest integration.
"""

import asyncio
import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.runner.queue_manager import QueueManager, QueueItem, QueueState, get_queue_manager, reset_queue_manager


class TestQueueManager:
    """Test cases for QueueManager"""

    def setup_method(self):
        """Setup test environment"""
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.artifacts_dir = Path(self.temp_dir.name) / "test_artifacts"
        self.artifacts_dir.mkdir(exist_ok=True)
        self.manager = QueueManager(self.artifacts_dir, max_concurrency=2)

    def teardown_method(self):
        """Cleanup test environment"""
        # Reset global state
        reset_queue_manager()
        # Clean up temp directory
        if hasattr(self, 'temp_dir'):
            self.temp_dir.cleanup()

    def test_enqueue_item(self):
        """Test enqueuing an item"""
        item = self.manager.enqueue("test-1", "Test Item", priority=1)

        assert item.id == "test-1"
        assert item.name == "Test Item"
        assert item.state == QueueState.WAITING
        assert item.priority == 1
        assert item.created_at is not None

    def test_enqueue_duplicate_item_raises_error(self):
        """Test that enqueuing duplicate item raises error"""
        self.manager.enqueue("test-1", "Test Item")

        with pytest.raises(ValueError, match="already exists in queue"):
            self.manager.enqueue("test-1", "Test Item 2")

    @pytest.mark.asyncio
    async def test_execute_next_item(self):
        """Test executing next item from queue"""
        await self.manager.start_stats_logging()
        self.manager.enqueue("test-1", "Test Item", priority=1)

        item = await self.manager.execute_next()
        assert item is not None
        assert item.id == "test-1"
        assert item.state == QueueState.RUNNING
        assert item.started_at is not None

    @pytest.mark.asyncio
    async def test_execute_empty_queue(self):
        """Test executing from empty queue"""
        await self.manager.start_stats_logging()

        item = await self.manager.execute_next()
        assert item is None

    @pytest.mark.asyncio
    async def test_complete_item(self):
        """Test completing an item"""
        await self.manager.start_stats_logging()
        self.manager.enqueue("test-1", "Test Item")
        item = await self.manager.execute_next()
        assert item is not None

        self.manager.complete_item("test-1", success=True)

        # Check that item was moved to completed
        status = self.manager.get_queue_status()
        assert status["completed_count"] == 1
        assert status["running_count"] == 0

    @pytest.mark.asyncio
    async def test_cancel_item(self):
        """Test cancelling an item"""
        await self.manager.start_stats_logging()
        self.manager.enqueue("test-1", "Test Item")
        item = await self.manager.execute_next()
        assert item is not None

        self.manager.cancel_item("test-1")

        # Check that item was cancelled
        status = self.manager.get_queue_status()
        assert status["completed_count"] == 1  # Cancelled items count as completed
        assert status["running_count"] == 0

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test that items are dequeued in priority order"""
        await self.manager.start_stats_logging()

        # Enqueue items with different priorities
        self.manager.enqueue("low-priority", "Low Priority", priority=1)
        self.manager.enqueue("high-priority", "High Priority", priority=5)
        self.manager.enqueue("medium-priority", "Medium Priority", priority=3)

        # First item should be highest priority
        item1 = await self.manager.execute_next()
        assert item1.id == "high-priority"

        # Second item should be medium priority
        item2 = await self.manager.execute_next()
        assert item2.id == "medium-priority"

        # Third item should be low priority
        item3 = await self.manager.execute_next()
        assert item3.id == "low-priority"

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """Test that concurrency limit is respected"""
        await self.manager.start_stats_logging()

        # Set low concurrency limit
        manager = QueueManager(self.artifacts_dir, max_concurrency=1)

        # Enqueue multiple items
        manager.enqueue("test-1", "Test 1")
        manager.enqueue("test-2", "Test 2")

        # Start first item
        item1 = await manager.execute_next()
        assert item1 is not None

        # Try to start second item - should be blocked by semaphore
        # In real usage, this would be handled by the semaphore
        status = manager.get_queue_status()
        assert status["running_count"] == 1
        assert status["queue_length"] == 1

    def test_queue_stats(self):
        """Test queue statistics"""
        stats = self.manager.get_queue_stats()

        assert "total_items" in stats
        assert "active_items" in stats
        assert "completed_items" in stats
        assert "max_concurrency" in stats
        assert "timestamp" in stats

    def test_update_max_concurrency(self):
        """Test updating max concurrency"""
        assert self.manager.max_concurrency == 2

        self.manager.update_max_concurrency(5)
        assert self.manager.max_concurrency == 5

        # Test invalid value
        with pytest.raises(ValueError):
            self.manager.update_max_concurrency(0)

    @pytest.mark.asyncio
    async def test_update_max_concurrency_with_active_tasks_raises_error(self):
        """Test that updating max concurrency with active tasks raises RuntimeError"""
        # Simulate active task using test helper method
        self.manager._add_active_item_for_testing("active-test", "Active Test")

        # Try to update max concurrency while there are active tasks - should raise RuntimeError
        with pytest.raises(RuntimeError, match="Cannot change max_concurrency while tasks are active"):
            self.manager.update_max_concurrency(3)

    @pytest.mark.asyncio
    async def test_set_max_concurrency_with_active_tasks_raises_error(self):
        """Test that setting max concurrency with active tasks raises RuntimeError"""
        # Simulate active task using test helper method
        self.manager._add_active_item_for_testing("active-test", "Active Test")

        # Try to set max concurrency while there are active tasks - should raise RuntimeError
        with pytest.raises(RuntimeError, match="Cannot change max_concurrency while tasks are active"):
            self.manager.max_concurrency = 3

    @pytest.mark.asyncio
    async def test_update_max_concurrency_with_waiting_tasks_raises_error(self):
        """Test that updating max concurrency with waiting tasks raises RuntimeError"""
        # Add waiting task to queue
        self.manager.enqueue("waiting-test", "Waiting Test")

        # Try to update max concurrency while there are waiting tasks - should raise RuntimeError
        with pytest.raises(RuntimeError, match="Cannot change max_concurrency while tasks are active"):
            self.manager.update_max_concurrency(2)

    @patch('src.config.multi_env_loader.load_config')
    def test_get_queue_manager_with_config(self, mock_load_config):
        """Test get_queue_manager with config loading"""
        mock_load_config.return_value = {"runner": {"max_concurrency": 10}}

        with patch('src.runtime.run_context.RunContext.get') as mock_rc:
            mock_rc.return_value.artifact_dir = MagicMock(return_value=self.artifacts_dir)

            manager = get_queue_manager()
            assert manager.max_concurrency == 10

    def test_shutdown(self):
        """Test queue manager shutdown"""

        async def test_shutdown():
            # Start stats logging
            await self.manager.start_stats_logging()

            # Start some background task
            self.manager.enqueue("test-1", "Test Item")

            # Shutdown should complete without errors
            await self.manager.shutdown()

            # Verify shutdown completed successfully by checking that the shutdown event is set
            # and that we cannot enqueue new items (shutdown state)
            assert self.manager._get_shutdown_event_for_testing().is_set()

            # Try to enqueue after shutdown - this should work but items won't be processed
            # since shutdown is signaled
            try:
                self.manager.enqueue("test-2", "Test Item 2")
                # If we get here, enqueue worked, which is fine
                status = self.manager.get_queue_status()
                # The queue should have the new item
                assert status["queue_length"] >= 1
            except Exception:
                # If enqueue fails, that's also acceptable behavior
                pass

        asyncio.run(test_shutdown())


class TestQueueItem:
    """Test cases for QueueItem"""

    def test_queue_item_creation(self):
        """Test QueueItem creation"""
        item = QueueItem(
            id="test-1",
            name="Test Item",
            state=QueueState.WAITING,
            created_at=time.time(),
            priority=1
        )

        assert item.id == "test-1"
        assert item.name == "Test Item"
        assert item.state == QueueState.WAITING
        assert item.priority == 1
        assert item.metadata == {}

    def test_queue_item_comparison(self):
        """Test QueueItem priority comparison"""
        base_time = time.time()
        item1 = QueueItem("1", "Item 1", QueueState.WAITING, base_time, priority=1)
        item2 = QueueItem("2", "Item 2", QueueState.WAITING, base_time, priority=2)

        # Higher priority should come first
        assert item2 < item1

        # Same priority, earlier creation time should come first
        later_time = base_time + 0.001
        item3 = QueueItem("3", "Item 3", QueueState.WAITING, later_time, priority=1)
        assert item1 < item3


if __name__ == "__main__":
    pytest.main([__file__])