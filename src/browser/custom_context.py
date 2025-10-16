
"""
Custom browser context management

This module provides LLM agent functionality and requires:
- ENABLE_LLM=true environment variable or feature flag
- Full requirements.txt installation (not requirements-minimal.txt)

When ENABLE_LLM=false, this module cannot be imported and will raise ImportError.
This ensures complete isolation of LLM dependencies for AI governance compliance.
"""

# Import guard: Block import when LLM functionality is disabled
try:
    from src.config.feature_flags import is_llm_enabled
    _ENABLE_LLM = is_llm_enabled()
except Exception:
    import os
    _ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"

if not _ENABLE_LLM:
    raise ImportError(
        "LLM agent functionality is disabled (ENABLE_LLM=false). "
        "This module requires full requirements.txt installation and ENABLE_LLM=true. "
        "To use agent features: "
        "1. Install full requirements: pip install -r requirements.txt "
        "2. Enable LLM: export ENABLE_LLM=true or set in .env file"
    )

import json
import logging
import os

from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import BrowserContext as PlaywrightBrowserContext

logger = logging.getLogger(__name__)


class CustomBrowserContext(BrowserContext):
    def __init__(
        self,
        browser: "Browser",
        config: BrowserContextConfig = BrowserContextConfig()
    ):
        super(CustomBrowserContext, self).__init__(browser=browser, config=config)