from src.modules.automation_manager import setup_browser_automation
import asyncio

async def main():
    # Initialize browser automation with target website
    website_url = "https://nogtips.wordpress.com"
    manager = setup_browser_automation(website_url)
    
    # Execute an action
    try:
        success = await manager.execute_action("search-nogtips", query="automation testing")
        if success:
            print("Action executed successfully")
        else:
            print("Action execution failed")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
