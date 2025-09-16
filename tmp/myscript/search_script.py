"""
Legacy entry point to maintain backwards compatibility with tmp/myscript path.

This forwards the main pytest test to the canonical myscript/search_script.py
so existing invocations like:

    pytest tmp/myscript/search_script.py --query foo

continue to work until all tooling/docs are updated.
"""

from __future__ import annotations

from myscript.search_script import test_text_search  # re-export for pytest collection