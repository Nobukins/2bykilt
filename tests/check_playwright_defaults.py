#!/usr/bin/env python3
"""
Playwrightのデフォルト引数を調査
"""
import asyncio
from playwright.async_api import async_playwright


async def check_playwright_default_args():
    """Playwrightのデフォルト引数を確認"""
    print("🔍 Playwrightのデフォルト引数を調査...")
    
    async with async_playwright() as p:
        # Chromiumブラウザを通常起動
        print("\n📊 通常のlaunch()の場合:")
        browser = await p.chromium.launch(headless=False)
        print(f"Browser launched: {browser}")
        await browser.close()
        
        # カスタム引数で起動
        print("\n📊 カスタム引数での起動:")
        custom_args = ["--disable-web-security"]
        browser = await p.chromium.launch(
            headless=False,
            args=custom_args
        )
        print(f"Browser launched with custom args: {browser}")
        await browser.close()
        
        # ignore_default_argsを使用
        print("\n📊 ignore_default_argsを使用:")
        browser = await p.chromium.launch(
            headless=False,
            ignore_default_args=True,  # すべてのデフォルト引数を無視
            args=["--disable-web-security"]
        )
        print(f"Browser launched ignoring defaults: {browser}")
        await browser.close()
        
        # 部分的にignore_default_argsを使用
        print("\n📊 特定の引数のみignore:")
        browser = await p.chromium.launch(
            headless=False,
            ignore_default_args=["--no-sandbox", "--disable-setuid-sandbox"],
            args=["--disable-web-security"]
        )
        print(f"Browser launched ignoring specific args: {browser}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(check_playwright_default_args())
