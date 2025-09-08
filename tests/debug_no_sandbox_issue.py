#!/usr/bin/env python3
"""
--no-sandbox引数の詳細調査
実際のブラウザ起動時の引数を詳細にログ出力して確認
"""
import asyncio
import os
import sys
import tempfile
import logging
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.profile_manager import ProfileManager
from src.utils.browser_launcher import BrowserLauncher

# ログレベルをDEBUGに設定
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')


async def debug_browser_args():
    """ブラウザ引数の詳細デバッグ"""
    print("🔍 --no-sandbox引数の詳細調査を開始...")
    
    # 一時ディレクトリ
    temp_dir = tempfile.mkdtemp()
    print(f"📁 テスト用ディレクトリ: {temp_dir}")
    
    try:
        # Chrome テスト
        print("\n🔴 Chrome引数デバッグ...")
        chrome_launcher = BrowserLauncher("chrome")
        
        # 引数を詳細に確認
        chrome_args = chrome_launcher._get_browser_args()
        print(f"📊 Chrome生成引数数: {len(chrome_args)}")
        print("🔧 Chrome生成引数一覧:")
        for i, arg in enumerate(chrome_args, 1):
            if "sandbox" in arg:
                print(f"  ⚠️  {i:2d}. {arg}")
            else:
                print(f"     {i:2d}. {arg}")
        
        # launch_optionsを確認
        chrome_profile_mgr = ProfileManager(
            source_profile_dir=os.environ.get('CHROME_USER_DATA', 
                                             '')
        )
        selenium_profile = chrome_profile_mgr.create_selenium_profile(temp_dir)
        
        launch_options = chrome_launcher._get_launch_options(selenium_profile)
        print(f"\n🔧 Chrome起動オプション:")
        print(f"  executable_path: {launch_options.get('executable_path')}")
        print(f"  headless: {launch_options.get('headless')}")
        print(f"  user_data_dir: {launch_options.get('user_data_dir')}")
        print(f"  args数: {len(launch_options.get('args', []))}")
        print("  args詳細:")
        for i, arg in enumerate(launch_options.get('args', []), 1):
            if "sandbox" in arg:
                print(f"    ⚠️  {i:2d}. {arg}")
            else:
                print(f"       {i:2d}. {arg}")
        
        # Playwrightの ignore_default_args を確認
        print(f"\n🔧 ignore_default_args: {launch_options.get('ignore_default_args')}")
        
        # 実際のブラウザ起動テスト
        print("\n🚀 実際のChrome起動テスト...")
        
        # Playwright のデバッグログを有効化
        os.environ['DEBUG'] = 'pw:api'
        
        try:
            context = await chrome_launcher.launch_with_profile(selenium_profile)
            print("✅ Chrome が起動しました")
            
            # コンテキストからブラウザ情報を取得
            if hasattr(context, '_browser'):
                browser = context._browser
                print(f"🔍 ブラウザ情報: {browser}")
            
            # 短時間待機
            await asyncio.sleep(3)
            
            # クローズ
            await context.close()
            print("✅ Chrome を正常にクローズしました")
            
        except Exception as e:
            print(f"❌ Chrome 起動エラー: {e}")
        
        # Edge テスト
        if Path("/Applications/Microsoft Edge.app").exists():
            print("\n🔵 Edge引数デバッグ...")
            edge_launcher = BrowserLauncher("edge")
            
            edge_args = edge_launcher._get_browser_args()
            print(f"📊 Edge生成引数数: {len(edge_args)}")
            print("🔧 Edge生成引数一覧:")
            for i, arg in enumerate(edge_args, 1):
                if "sandbox" in arg:
                    print(f"  ⚠️  {i:2d}. {arg}")
                else:
                    print(f"     {i:2d}. {arg}")
        
        return True
        
    finally:
        # クリーンアップ
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        # デバッグログを無効化
        os.environ.pop('DEBUG', None)


if __name__ == "__main__":
    asyncio.run(debug_browser_args())
