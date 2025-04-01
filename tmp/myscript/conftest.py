import pytest
import pytest_asyncio

# Register the asyncio plugin
pytest_plugins = ["pytest_asyncio"]

def pytest_configure(config):
    """Configure pytest with asyncio markers"""
    config.addinivalue_line("markers", "asyncio: mark test to run with asyncio")

def pytest_addoption(parser):
    parser.addoption("--query", action="store", default="", help="Search query for the test")