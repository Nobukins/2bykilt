import pytest
import pytest_asyncio

# Register the asyncio plugin
# pytest_plugins = ["pytest_asyncio"]

def pytest_configure(config):
    """Configure pytest with asyncio markers"""
    config.addinivalue_line("markers", "asyncio: mark test to run with asyncio")

def pytest_addoption(parser):
    parser.addoption("--query", action="store", default="", help="Search query for the test")
    parser.addoption("--browser-type", action="store", default=None, help="Browser type to use (chrome/edge/firefox/webkit)")
    parser.addoption("--browser-executable", action="store", default=None, help="Path to browser executable")
    parser.addoption("--use-profile", action="store_true", default=False, help="Use user profile for Chrome/Edge")
    parser.addoption("--profile-path", action="store", default=None, help="Custom user profile path")