"""Memory monitoring light test (module may be optional)."""

import importlib
import pytest


def test_memory_monitor_optional_import():
	try:
		import src.utils.memory_monitor as mm  # type: ignore
	except ImportError:
		pytest.skip("memory_monitor module not present in minimal install")
		return
	importlib.reload(mm)
	# Module should expose at least 'memory_monitor'
	assert hasattr(mm, "memory_monitor")

