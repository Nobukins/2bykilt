async def close_global_browser():
    """Close the global browser and update browser use configuration."""
    globals_dict = get_globals()
    browser_context = globals_dict["browser_context"]
    browser = globals_dict["browser"]

    if browser_context:
        await browser_context.close()

    if browser:
        await browser.close()

    # Update global configuration to ensure next browser creation respects the setting
    globals_dict["use_own_browser_config"] = True

    return True
