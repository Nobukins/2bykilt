import os
import sys
import subprocess
import tempfile
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

def get_default_edge_user_data():
    """Get the default Edge user data directory based on the OS"""
    if sys.platform == 'win32':  # Windows
        return os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")
    elif sys.platform == 'darwin':  # macOS
        return os.path.expanduser("~/Library/Application Support/Microsoft Edge")
    else:  # Linux
        return os.path.expanduser("~/.config/microsoft-edge")

def detect_browser_paths():
    """ブラウザパスとユーザーデータディレクトリを検出"""
    # Edge検出
    edge_path = os.getenv("EDGE_PATH", "")
    edge_user_data = os.getenv("EDGE_USER_DATA", "")
    
    if not edge_path:
        if sys.platform == 'win32':  # Windows
            possible_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            ]
        elif sys.platform == 'darwin':  # macOS
            possible_paths = [
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
            ]
        else:  # Linux
            possible_paths = [
                "/usr/bin/microsoft-edge",
                "/usr/bin/microsoft-edge-stable"
            ]
        for path in possible_paths:
            if os.path.exists(path):
                edge_path = path
                os.environ["EDGE_PATH"] = path
                logger.info(f"✅ Edgeパスを検出: {path}")
                break
    
    if not edge_user_data:
        default_edge_data = get_default_edge_user_data()
        if os.path.exists(default_edge_data):
            edge_user_data = default_edge_data
            os.environ["EDGE_USER_DATA"] = default_edge_data
            logger.info(f"✅ Edgeユーザーデータディレクトリを検出: {default_edge_data}")
    
    return {
        "edge_path": edge_path,
        "edge_user_data": edge_user_data
    }

def run_playwright_codegen(url, browser_type='chrome'):
    """
    指定URLに対してplaywright codegenを実行し、生成スクリプトを取得。
    browser_typeは 'chrome' または 'edge'
    """
    if browser_type.lower() == 'edge':
        return run_edge_codegen(url)
    else:
        return run_normal_codegen(url)

def run_normal_codegen(url):
    """
    通常のPlaywright codegenコマンドを実行（Chromeなど）
    """
    try:
        fd, temp_path = tempfile.mkstemp(suffix='.py')
        os.close(fd)
        
        cmd = ["playwright", "codegen", url, "--target", "python", "-o", temp_path]
        logger.info(f"実行するコマンド: {' '.join(cmd)}")
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=300)
        
        if process.returncode == 0 and os.path.exists(temp_path):
            with open(temp_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            script_content = convert_to_action_format(script_content)
            os.unlink(temp_path)
            return True, script_content
        else:
            error_msg = stderr.decode('utf-8') if stderr else "不明なエラー"
            return False, f"Playwright codegen実行エラー: {error_msg}"
    except subprocess.TimeoutExpired:
        process.kill()
        return False, "Playwright codegenが5分後にタイムアウトしました"
    except Exception as e:
        logger.error(f"Playwright codegen実行失敗: {str(e)}")
        return False, f"Playwright codegen実行失敗: {str(e)}"

def run_edge_codegen(url):
    """
    EdgeブラウザでPlaywright codegenを実行
    """
    try:
        # 一時ファイルを作成して出力先にする
        fd, temp_path = tempfile.mkstemp(suffix='.py')
        os.close(fd)
        
        # ブラウザパスとユーザーデータディレクトリを検出
        browser_paths = detect_browser_paths()
        user_data_dir = browser_paths.get("edge_user_data", "")
        
        # コマンドを構築
        cmd = [
            "playwright", "codegen",
            url,
            "--target", "python",
            "-o", temp_path,
            "--browser", "chromium",  # chromiumを指定
            "--channel", "msedge"     # チャネルとしてmsedgeを指定
        ]
        
        # 環境変数を設定
        env = os.environ.copy()
        if user_data_dir and os.path.exists(user_data_dir):
            env["PLAYWRIGHT_BROWSERS_PATH"] = "0"  # ブラウザをダウンロードさせない
            env["PLAYWRIGHT_MSEDGE_USER_DATA_DIR"] = user_data_dir
            logger.info(f"Edgeユーザーデータディレクトリ: {user_data_dir}")
        
        logger.info(f"実行するコマンド: {' '.join(cmd)}")
        logger.info(f"環境変数PLAYWRIGHT_MSEDGE_USER_DATA_DIR設定済み: {user_data_dir}")
        
        # コマンド実行
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        
        # ユーザーが操作を終えるのを待つ
        stdout, stderr = process.communicate(timeout=600)  # 10分のタイムアウト
        
        # 結果確認
        if process.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            with open(temp_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            script_content = convert_to_action_format(script_content)
            os.unlink(temp_path)
            return True, script_content
        else:
            # エラー内容を詳細に表示
            logger.error(f"Playwright codegen終了コード: {process.returncode}")
            logger.error(f"標準出力: {stdout.decode('utf-8', errors='replace')}")
            logger.error(f"標準エラー: {stderr.decode('utf-8', errors='replace')}")
            
            if os.path.exists(temp_path):
                if os.path.getsize(temp_path) == 0:
                    return False, "操作記録ファイルが空です。ブラウザで何か操作を行ってください。"
                else:
                    # ファイルは存在するが、他の理由でエラーが起きた場合
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        script_content = f.read()
                    script_content = convert_to_action_format(script_content)
                    os.unlink(temp_path)
                    return True, script_content
            
            error_msg = stderr.decode('utf-8', errors='replace') if stderr else "不明なエラー"
            return False, f"Playwright codegen実行エラー: {error_msg}"
            
    except subprocess.TimeoutExpired:
        process.kill()
        return False, "Playwright codegenのタイムアウト（10分）。長時間の操作は分割して記録してください。"
    except Exception as e:
        logger.error(f"Playwright codegen実行エラー: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Playwright codegen実行エラー: {str(e)}"

def convert_to_action_format(script_content):
    """
    Convert the playwright codegen output to action_runner_template format.
    """
    lines = script_content.splitlines()
    action_lines = []
    for line in lines:
        if line.startswith('from playwright') or line.startswith('import ') or line.startswith('#') or not line.strip():
            continue
        if 'playwright.sync_api' in line or '.launch(' in line or '.new_context(' in line or '.new_page(' in line or '.close(' in line:
            continue
        if '.goto(' in line or '.click(' in line or '.fill(' in line or '.check(' in line or '.press(' in line or '.wait_for' in line:
            if not line.strip().startswith('await '):
                line = re.sub(r'(\s*)(page\.\w+\()', r'\1await \2', line)
            action_lines.append(line)
    
    template = """async def run_actions(page, query=None):
    # Auto-generated from playwright codegen
    """
    for line in action_lines:
        template +=     f"{line}\n"
    template += "    await page.wait_for_timeout(3000)\n"
    return template

def save_as_action_file(script_content, file_name, action_name=None):
    """
    Save the script content as a new action file and update llms.txt.
    
    Args:
        script_content (str): Script content to save
        file_name (str): File name (without extension)
        action_name (str, optional): Custom name for the action. Defaults to file_name.
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Ensure file_name has .py extension
        if not file_name.endswith('.py'):
            file_name_org = file_name
            file_name += '.py'
            
        # Default action_name to file_name without extension if not provided
        if action_name is None or action_name.strip() == '':
            action_name = os.path.splitext(file_name)[0]
            
        # Get the actions directory path
        root_dir = Path(__file__).parent.parent.parent
        actions_dir = root_dir / 'tmp/myscript/actions'
        
        # Create actions directory if it doesn't exist
        if not actions_dir.exists():
            actions_dir.mkdir(parents=True)
            
        # Full path to save the action file
        file_path = actions_dir / file_name
        
        # Save the script content to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
            
        # Update llms.txt
        llms_path = root_dir / 'llms.txt'
        new_entry = f"""
  - name: {action_name}
    type: action_runner_template
    action_script: {file_name_org}
    params:
      - name: query
        required: true
        type: string
        description: "検索クエリ"
    command: python ./tmp/myscript/action_runner.py --action ${{action_script}} --query "${{params.query}}" --slowmo 1500 --countdown 3
"""
        if llms_path.exists():
            # Read existing content
            with open(llms_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check if entry already exists
            if f"name: {action_name}" in content:
                return True, f"Action file saved but entry already exists in llms.txt"
                
            # Append new entry to llms.txt
            with open(llms_path, 'a', encoding='utf-8') as f:
                f.write(new_entry)
        else:
            # Create llms.txt if it doesn't exist
            with open(llms_path, 'w', encoding='utf-8') as f:
                f.write(f"actions:{new_entry}")
                
        return True, f"Successfully saved action file and added to llms.txt: {action_name}"
    except Exception as e:
        logger.error(f"Failed to save action file: {str(e)}")
        return False, f"Failed to save action file: {str(e)}"
