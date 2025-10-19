import asyncio
import pytest
from src.utils.timeout_manager import TimeoutManager, TimeoutScope, TimeoutError, CancellationError


@pytest.mark.ci_safe
@pytest.mark.asyncio
async def test_timeout_scope_success():
    """Test that timeout_scope works correctly for operations that complete within timeout"""
    tm = TimeoutManager()

    async def quick_operation():
        await asyncio.sleep(0.1)
        return "success"

    async with tm.timeout_scope(TimeoutScope.OPERATION, 1):
        result = await quick_operation()

    assert result == "success"


@pytest.mark.ci_safe
@pytest.mark.asyncio
async def test_timeout_scope_timeout():
    """Test that timeout_scope raises TimeoutError for operations that exceed timeout"""
    tm = TimeoutManager()

    async def slow_operation():
        await asyncio.sleep(2)  # Longer than timeout
        return "should not reach here"

    with pytest.raises(TimeoutError):
        async with tm.timeout_scope(TimeoutScope.OPERATION, 1):
            await slow_operation()


@pytest.mark.ci_safe
@pytest.mark.asyncio
async def test_timeout_scope_cancellation():
    """Test that timeout_scope handles cancellation correctly"""
    tm = TimeoutManager()

    async def cancellable_operation():
        await asyncio.sleep(2)

    # Cancel the manager
    tm.cancel()

    with pytest.raises((CancellationError, asyncio.CancelledError)):
        async with tm.timeout_scope(TimeoutScope.OPERATION, 5):
            await cancellable_operation()