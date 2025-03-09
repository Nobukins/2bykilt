# conftest.py
def pytest_addoption(parser):
    parser.addoption("--query", action="store", default="", help="Search query for the test")