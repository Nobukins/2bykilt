import asyncio
import argparse
import importlib.util
import os
import sys
from pathlib import Path
from datetime import datetime
import json
from browser_base import BrowserAutomationBase

def log_message(message):
    """ログメッセージを標準出力、標準エラー出力、およびファイルに出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    
    # 標準出力と標準エラー出力
    print(formatted_message)
    print(formatted_message, file=sys.stderr)
    sys.stdout.flush()
    sys.stderr.flush()
    
    # ログファイルにも出力
    try:
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "action_runner_debug.log"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{formatted_message}\n")
            f.flush()
    except Exception as e:
        print(f"ログファイル書き込みエラー: {e}", file=sys.stderr)

def ensure_recording_path():
    """RECORDING_PATH環境変数を確認し、ディレクトリを作成"""
    recording_path = os.environ.get("RECORDING_PATH")
    if not recording_path:
        log_message("❌ [action_runner] エラー: RECORDING_PATH環境変数が設定されていません。")
        log_message("💡 [action_runner] 例: export RECORDING_PATH=/path/to/recordings")
        sys.exit(1)
    
    recording_dir = Path(recording_path)
    recording_dir.mkdir(parents=True, exist_ok=True)
    log_message(f"📁 [action_runner] RECORDING_PATH確認: {recording_dir}")
    return recording_dir

def get_base_dir():
    """プロジェクトのベースディレクトリを取得"""
    # __file__の3階層上（myscript/の親ディレクトリ）
    return Path(__file__).parent.parent.parent

def collect_artifacts(source_dir, target_dir, action_name):
    """生成物をartifacts/に収集し、Tab-XXプレフィックスを適用"""
    if not source_dir.exists():
        log_message(f"⚠️ [action_runner] ソースディレクトリが存在しません: {source_dir}")
        return []
    
    artifacts_dir = get_base_dir() / "artifacts" / action_name
    try:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log_message(f"❌ [action_runner] アーティファクトディレクトリ作成エラー: {e}")
        return []
    
    collected_files = []
    tab_index = 1
    
    # 動画ファイルとスクリーンショットを収集
    for file_path in source_dir.glob("*.webm"):
        try:
            new_name = f"Tab-{tab_index:02d}-{file_path.name}"
            new_path = artifacts_dir / new_name
            file_path.rename(new_path)
            collected_files.append({
                "index": tab_index,
                "original_name": file_path.name,
                "new_name": new_name,
                "path": str(new_path),
                "type": "video"
            })
            tab_index += 1
            log_message(f"📹 [action_runner] 動画ファイル収集: {new_name}")
        except Exception as e:
            log_message(f"❌ [action_runner] 動画ファイル移動エラー: {file_path} -> {e}")
    
    for file_path in source_dir.glob("*.png"):
        try:
            new_name = f"Tab-{tab_index:02d}-{file_path.name}"
            new_path = artifacts_dir / new_name
            file_path.rename(new_path)
            collected_files.append({
                "index": tab_index,
                "original_name": file_path.name,
                "new_name": new_name,
                "path": str(new_path),
                "type": "screenshot"
            })
            tab_index += 1
            log_message(f"📸 [action_runner] スクリーンショット収集: {new_name}")
        except Exception as e:
            log_message(f"❌ [action_runner] スクリーンショット移動エラー: {file_path} -> {e}")
    
    return collected_files

def generate_manifest(artifacts, action_name):
    """アーティファクトのmanifestを生成"""
    artifacts_dir = get_base_dir() / "artifacts" / action_name
    manifest_path = artifacts_dir / "tab_index_manifest.json"
    
    manifest = {
        "action": action_name,
        "timestamp": datetime.now().isoformat(),
        "artifacts": artifacts,
        "summary": {
            "total_files": len(artifacts),
            "videos": len([a for a in artifacts if a["type"] == "video"]),
            "screenshots": len([a for a in artifacts if a["type"] == "screenshot"])
        }
    }
    
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        log_message(f"📋 [action_runner] Manifest生成完了: {manifest_path}")
        return manifest_path
    except Exception as e:
        log_message(f"❌ [action_runner] Manifest生成エラー: {e}")
        return None

async def run_scenario(action_file, query=None, slowmo=0, headless=False, countdown=5, browser_type="chromium"):
    """
    指定されたアクションファイルを使用してブラウザ自動化シナリオを実行
    
    Args:
        action_file: アクションファイルのパス
        query: 検索クエリ文字列
        slowmo: スローモーションの時間 (ミリ秒)
        headless: ヘッドレスモードで実行するかどうか
        countdown: カウントダウン時間 (秒)
        browser_type: ブラウザタイプ ("chromium", "chrome", "msedge", "firefox", "webkit")
    """
    log_message(f"🚀 [action_runner] シナリオ開始 - ファイル: {action_file}")
    log_message(f"🔍 [action_runner] パラメータ - query: {query}, slowmo: {slowmo}, headless: {headless}, countdown: {countdown}, browser: {browser_type}")
    
    # RECORDING_PATHの確認
    recording_dir = ensure_recording_path()
    action_name = Path(action_file).stem
    
    # アクションモジュールの動的読み込み
    if not os.path.exists(action_file):
        log_message(f"❌ [action_runner] エラー: アクションファイル '{action_file}' が見つかりません。")
        return False
    
    log_message(f"📁 [action_runner] アクションファイルを読み込み中...")
    module_name = Path(action_file).stem
    spec = importlib.util.spec_from_file_location(module_name, action_file)
    action_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(action_module)
    
    if not hasattr(action_module, "run_actions"):
        log_message(f"❌ [action_runner] エラー: {action_file} に run_actions 関数が定義されていません。")
        return False
    
    log_message(f"✅ [action_runner] アクションモジュール読み込み完了: {module_name}")
    
    # ブラウザ自動化の準備
    log_message(f"🌐 [action_runner] ブラウザ自動化を準備中...")
    automation = BrowserAutomationBase(headless=headless, slowmo=slowmo, browser_type=browser_type)
    try:
        # ブラウザを設定
        log_message(f"🔧 [action_runner] ブラウザセットアップ中...")
        page = await automation.setup()
        log_message(f"✅ [action_runner] ブラウザセットアップ完了")
        
        # 自動操作インジケータを表示
        log_message(f"📢 [action_runner] 自動操作インジケータ表示中...")
        await automation.show_automation_indicator()
        
        # アクションを実行
        log_message(f"🎬 [action_runner] アクション実行開始...")
        await action_module.run_actions(page, query)
        log_message(f"✅ [action_runner] アクション実行完了")
        
        # 終了カウントダウン
        log_message(f"⏰ [action_runner] 終了カウントダウン開始 ({countdown}秒)...")
        await automation.show_countdown_overlay(seconds=countdown)
        
        log_message(f"🎉 [action_runner] シナリオ正常終了")
        return True
    except Exception as e:
        log_message(f"❌ [action_runner] エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # リソース解放
        log_message(f"🧹 [action_runner] リソース解放中...")
        await automation.cleanup()
        log_message(f"🧹 [action_runner] リソース解放完了")
        
        # 生成物の収集と整理
        log_message(f"📦 [action_runner] 生成物収集中...")
        collected_artifacts = collect_artifacts(recording_dir, get_base_dir() / "artifacts", action_name)
        
        if collected_artifacts:
            log_message(f"📋 [action_runner] Manifest生成中...")
            manifest_path = generate_manifest(collected_artifacts, action_name)
            log_message(f"✅ [action_runner] {len(collected_artifacts)}個のファイルをartifacts/{action_name}/に移動しました")
        else:
            log_message(f"⚠️ [action_runner] 収集可能な生成物が見つかりませんでした")

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
    
    with open(file_path, "w", encoding="utf-8") as f:
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
    log_message(f"🎯 [action_runner] プログラム開始 - 引数: {sys.argv}")
    
    parser = argparse.ArgumentParser(description="ブラウザ自動化アクションランナー")
    parser.add_argument("--action", help="実行するアクションファイル名")
    parser.add_argument("--query", help="検索クエリ")
    parser.add_argument("--slowmo", type=int, default=0, help="スロー実行の時間 (ミリ秒)")
    parser.add_argument("--headless", action="store_true", help="ヘッドレスモードで実行")
    parser.add_argument("--countdown", type=int, default=5, help="終了カウントダウン時間 (秒)")
    parser.add_argument("--browser", choices=["chromium", "chrome", "msedge", "edge", "firefox", "webkit"], 
                        default=os.environ.get("BYKILT_BROWSER_TYPE", "chromium"), help="使用するブラウザタイプ")
    parser.add_argument("--new", help="新しいアクションテンプレートを作成")
    parser.add_argument("--list", action="store_true", help="利用可能なアクションを一覧表示")
    
    args = parser.parse_args()
    log_message(f"📋 [action_runner] 解析された引数: {args}")
    
    if args.new:
        log_message(f"🆕 [action_runner] 新しいテンプレート作成: {args.new}")
        create_action_template(args.new)
    elif args.list:
        log_message(f"📄 [action_runner] アクションリスト表示")
        list_actions()
    elif args.action:
        log_message(f"🎬 [action_runner] アクション実行モード: {args.action}")
        actions_dir = Path(__file__).parent / "actions"
        action_file = actions_dir / f"{args.action}.py"
        log_message(f"📂 [action_runner] アクションファイルパス: {action_file}")
        
        if not action_file.exists():
            log_message(f"❌ [action_runner] エラー: アクションファイル '{action_file}' が見つかりません。")
            sys.exit(1)
        
        log_message(f"🚀 [action_runner] asyncio.run でシナリオ実行開始...")
        result = asyncio.run(run_scenario(
            action_file, 
            query=args.query, 
            slowmo=args.slowmo, 
            headless=args.headless,
            countdown=args.countdown,
            browser_type=args.browser
        ))
        log_message(f"🏁 [action_runner] シナリオ実行結果: {result}")
    else:
        log_message(f"❓ [action_runner] ヘルプ表示")
        parser.print_help()
