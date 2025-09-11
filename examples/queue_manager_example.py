"""
Example usage of QueueManager for Issue #47

This example demonstrates how to use the QueueManager for concurrent execution
control with configurable concurrency limits.
"""

import asyncio
import time
from pathlib import Path
from src.runner.queue_manager import get_queue_manager


async def example_worker(item_id: str, name: str) -> str:
    """
    Example worker function that simulates some work

    Args:
        item_id: Unique identifier for the work item
        name: Human-readable name

    Returns:
        Result string
    """
    print(f"Starting work on {item_id}: {name}")

    # Simulate some work
    await asyncio.sleep(1.0)

    result = f"Completed {item_id}: {name}"
    print(result)
    return result


async def producer(manager, num_items: int = 10):
    """
    Producer that enqueues work items

    Args:
        manager: QueueManager instance
        num_items: Number of items to enqueue
    """
    print(f"Enqueuing {num_items} work items...")

    for i in range(num_items):
        priority = (i % 3) + 1  # Priorities 1, 2, 3
        item_id = f"work-{i:03d}"
        name = f"Work Item {i}"

        manager.enqueue(item_id, name, priority=priority)
        print(f"Enqueued: {item_id} (priority={priority})")

        # Small delay between enqueues
        await asyncio.sleep(0.1)


async def consumer(manager):
    """
    Consumer that processes work items from the queue

    Args:
        manager: QueueManager instance
    """
    print("Starting consumer...")

    while True:
        # Get next item to process
        item = await manager.execute_next()

        if item is None:
            # No more items in queue
            print("No more items in queue")
            break

        print(f"Processing: {item.id} ({item.name}) priority={item.priority}")

        try:
            # Do the work
            result = await example_worker(item.id, item.name)

            # Mark as completed
            manager.complete_item(item.id, success=True)
            print(f"Completed: {item.id}")

        except Exception as e:
            print(f"Failed to process {item.id}: {e}")
            manager.complete_item(item.id, success=False)


async def monitor(manager, duration: float = 5.0):
    """
    Monitor that periodically prints queue status

    Args:
        manager: QueueManager instance
        duration: How long to monitor
    """
    start_time = time.time()

    while time.time() - start_time < duration:
        status = manager.get_queue_status()
        stats = manager.get_queue_stats()

        print(f"\n--- Queue Status ---")
        print(f"Queue length: {status['queue_length']}")
        print(f"Running: {status['running_count']}")
        print(f"Completed: {status['completed_count']}")
        print(f"Max concurrency: {status['max_concurrency']}")
        print(f"Avg wait time: {stats.get('avg_wait_time', 0):.2f}s")
        print(f"Total enqueued: {stats.get('total_items', 0)}")

        if status['waiting_items']:
            print("Waiting items (top 3):")
            for item in status['waiting_items'][:3]:
                print(f"  - {item['id']}: {item['name']} (priority={item['priority']}, wait={item['wait_time']:.1f}s)")

        await asyncio.sleep(1.0)


async def main():
    """
    Main example function demonstrating QueueManager usage
    """
    print("=== QueueManager Example for Issue #47 ===")

    # Get queue manager (will load config automatically)
    manager = get_queue_manager(max_concurrency=3)

    # Start stats logging
    await manager.start_stats_logging()

    print(f"QueueManager initialized with max_concurrency={manager.max_concurrency}")

    # Create tasks
    producer_task = asyncio.create_task(producer(manager, num_items=8))
    consumer_task = asyncio.create_task(consumer(manager))
    monitor_task = asyncio.create_task(monitor(manager, duration=10.0))

    # Wait for producer to finish
    await producer_task

    # Wait for consumer to finish processing all items
    await consumer_task

    # Cancel monitor
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

    # Final status
    final_status = manager.get_queue_status()
    final_stats = manager.get_queue_stats()

    print("\n=== Final Results ===")
    print(f"Total enqueued: {final_stats.get('total_items', 0)}")
    print(f"Total completed: {final_status['completed_count']}")
    print(f"Average wait time: {final_stats.get('avg_wait_time', 0):.2f}s")
    print(f"Average run time: {final_stats.get('avg_run_time', 0):.2f}s")

    # Shutdown gracefully
    await manager.shutdown()

    print("Example completed successfully!")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())