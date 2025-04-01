import asyncio
import argparse
import importlib.util
import os
import sys
from pathlib import Path
from browser_base import BrowserAutomationBase

async def run_scenario(action_file, query=None, slowmo=0, headless=False, countdown=5):
    """
    指定されたアクションファイルを使用してブラウザ自動化シナリオを実行
    
    Args:
        action_file: アクションファイルのパス
        query: 検索クエリ文字列
        slowmo: スローモーションの時間 (ミリ秒)
        headless: ヘッドレスモードで実行するかどうか
        countdown: カウントダウン時間 (秒)
    """
    # アクションモジュールの動的読み込み
    if not os.path.exists(action_file):
        print(f"エラー: アクションファイル '{action_file}' が見つかりません。")
        return False
    
    module_name = Path(action_file).stem
    spec = importlib.util.spec_from_file_location(module_name, action_file)
    action_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(action_module)
    
    if not hasattr(action_module, "run_actions"):
        print(f"エラー: {action_file} に run_actions 関数が定義されていません。")
        return False
    
    # ブラウザ自動化の準備
    automation = BrowserAutomationBase(headless=headless, slowmo=slowmo)
    try:
        # ブラウザを設定
        page = await automation.setup()
        
        # 自動操作インジケータを表示
        await automation.show_automation_indicator()
        
        # アクションを実行
        await action_module.run_actions(page, query)
        
        # 終了カウントダウン
        await automation.show_countdown_overlay(seconds=countdown)
        
        return True
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # リソース解放
        await automation.cleanup()

def create_action_template(action_name):
    """新しいアクションファイルのテンプレートを作成"""
    actions_dir = Path(__file__).parent / "actions"
    actions_dir.mkdir(exist_ok=True)
    
    file_path = actions_dir / f"{action_name}.py"
    if file_path.exists():
        print(f"警告: {file_path} はすでに存在します。上書きせずに終了します。")
        return
    
    template = '''async def run_actions(page, query=None):
    """
    ブラウザ自動化アクション
    
    Args:
        page: Playwrightのページオブジェクト
        query: 検索クエリ (文字列)
    """
    # ここに自動化アクションを記述
    # playwright codegenで生成したコードをここに貼り付けられます
    await page.goto("https://example.com")
    
    # 検索クエリを使用する例
    if query:
        await page.fill("input[name=q]", query)
        await page.press("input[name=q]", "Enter")
    
    # 結果を表示する時間
    await page.wait_for_timeout(5000)
'''
    
    with open(file_path, "w") as f:
        f.write(template)
    
    print(f"✅ テンプレートファイルを作成しました: {file_path}")
    print("このファイルを編集して、playwrightのcodegenで生成したコードを貼り付けてください。")

def list_actions():
    """利用可能なアクションファイルを一覧表示"""
    actions_dir = Path(__file__).parent / "actions"
    if not actions_dir.exists():
        print("アクションディレクトリが見つかりません。")
        return
    
    action_files = list(actions_dir.glob("*.py"))
    if not action_files:
        print("アクションファイルが見つかりません。")
        return
    
    print(f"\n利用可能なアクションファイル ({len(action_files)}個):")
    for i, file_path in enumerate(action_files):
        print(f"{i+1}. {file_path.stem}")
    
    print("\n使用例:")
    print(f"python {Path(__file__).name} --action {action_files[0].stem} --query 'テスト検索'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ブラウザ自動化アクションランナー")
    parser.add_argument("--action", help="実行するアクションファイル名")
    parser.add_argument("--query", help="検索クエリ")
    parser.add_argument("--slowmo", type=int, default=0, help="スロー実行の時間 (ミリ秒)")
    parser.add_argument("--headless", action="store_true", help="ヘッドレスモードで実行")
    parser.add_argument("--countdown", type=int, default=5, help="終了カウントダウン時間 (秒)")
    parser.add_argument("--new", help="新しいアクションテンプレートを作成")
    parser.add_argument("--list", action="store_true", help="利用可能なアクションを一覧表示")
    
    args = parser.parse_args()
    
    if args.new:
        create_action_template(args.new)
    elif args.list:
        list_actions()
    elif args.action:
        actions_dir = Path(__file__).parent / "actions"
        action_file = actions_dir / f"{args.action}.py"
        
        if not action_file.exists():
            print(f"エラー: アクションファイル '{action_file}' が見つかりません。")
            sys.exit(1)
        
        asyncio.run(run_scenario(
            action_file, 
            query=args.query, 
            slowmo=args.slowmo, 
            headless=args.headless,
            countdown=args.countdown
        ))
    else:
        parser.print_help()
