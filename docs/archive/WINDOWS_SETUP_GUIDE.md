# Windows環境セットアップガイド 🪟

## 🚀 クイックスタート（Windows 10/11対応）

### 必須事前準備

```powershell
# 1. Python 3.12+インストール確認
python --version

# 2. 仮想環境作成・有効化
python -m venv .venv
.venv\Scripts\activate

# 3. 依存関係インストール
pip install -r requirements-minimal.txt

# 4. Playwright ブラウザセットアップ
playwright install chromium
```

## 🛠️ Windows固有の設定

### 環境変数設定（.env ファイル）

```env
# Windows Chrome設定
CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
CHROME_DEBUGGING_PORT=9222
CHROME_USER_DATA=

# Edge利用の場合
EDGE_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
EDGE_USER_DATA=

# 録画設定（パスはWindowsスタイル）
RECORDING_PATH=C:\Users\%USERNAME%\Documents\2bykilt\recordings

# LLM機能（初期セットアップでは無効推奨）
ENABLE_LLM=false
```

### ブラウザ自動検出設定

bykiltは以下の順序でChromeを自動検出します：

1. `CHROME_PATH` 環境変数
2. `C:\Program Files\Google\Chrome\Application\chrome.exe`
3. `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
4. `%USERPROFILE%\AppData\Local\Google\Chrome\Application\chrome.exe`

## 🔧 Windows特有の問題と解決策

### 問題1: "playwright not found" エラー

**症状**: `subprocess` 実行時にplaywrightモジュールが見つからない

**解決策**:
```powershell
# 1. 仮想環境が有効か確認
echo $env:VIRTUAL_ENV

# 2. playwrightが正しくインストールされているか確認
pip list | Select-String playwright

# 3. Python実行パスを明示的に設定
$env:PYTHONPATH = (Get-Location).Path

# 4. アプリ起動
python bykilt.py
```

### 問題2: Chrome起動失敗

**症状**: Chromeプロセスの起動や制御に失敗

**解決策**:
```powershell
# 1. Chrome実行ファイル確認
Test-Path "C:\Program Files\Google\Chrome\Application\chrome.exe"

# 2. Chromeプロセス強制終了
taskkill /F /IM chrome.exe

# 3. デバッグポート確認
netstat -an | Select-String 9222

# 4. 管理者権限で実行（必要に応じて）
Start-Process PowerShell -Verb RunAs
```

### 問題3: パス区切り文字エラー

**症状**: Unixスタイルのパス（`/`）が使われてエラー

**解決策**: 自動修正済み - bykiltは `pathlib` を使用してクロスプラットフォーム対応済み

### 問題4: 権限エラー

**症状**: 録画ディレクトリや一時ファイルの作成に失敗

**解決策**:
```powershell
# 1. 書き込み権限のあるディレクトリに変更
$env:RECORDING_PATH = "$env:USERPROFILE\Documents\2bykilt_recordings"

# 2. 一時ディレクトリ権限確認
New-Item -ItemType Directory -Path ".\tmp\record_videos" -Force
```

## 📱 動作確認手順

### 1. 基本動作テスト
```powershell
# テスト用最小スクリプト作成
@"
import gradio as gr
with gr.Blocks() as demo:
    gr.Textbox(label="Windows Test", placeholder="動作確認中...")
    gr.Button("テスト実行")
demo.launch(server_port=7861, share=False)
"@ | Out-File -FilePath test_windows.py -Encoding UTF8

# 実行
python test_windows.py
```

### 2. ブラウザ連携テスト
```powershell
# Chrome起動確認
python -c "
import asyncio
from src.browser.browser_manager import initialize_browser
async def test():
    result = await initialize_browser(use_own_browser=True, headless=False)
    print('Browser test:', result)
asyncio.run(test())
"
```

### 3. 自動化機能テスト
```powershell
python bykilt.py
# ブラウザで http://localhost:7860/ にアクセス
# "テスト用コマンド実行" で動作確認
```

## 🚨 トラブルシューティング

### Windows Defender/ウイルス対策ソフト

一部のウイルス対策ソフトでplaywrightやChromeの自動制御がブロックされる場合があります：

```powershell
# 1. 除外設定に追加
# - プロジェクトフォルダ全体
# - .venv フォルダ
# - Chrome実行ファイル

# 2. リアルタイム保護を一時無効化（テスト時のみ）
# Windows Defender -> ウイルスと脅威の防止 -> リアルタイム保護
```

### ファイアウォール設定

```powershell
# 必要に応じてポート開放
New-NetFirewallRule -DisplayName "2bykilt" -Direction Inbound -Protocol TCP -LocalPort 7860,9222 -Action Allow
```

### 詳細ログ有効化

```powershell
# デバッグモードで起動
$env:DEBUG = "true"
python bykilt.py --debug
```

## 📝 Windows環境でのベストプラクティス

1. **管理者権限での実行は避ける**: 通常ユーザー権限で動作するよう設計済み
2. **長いパス名の回避**: プロジェクトはC直下など短いパスに配置推奨
3. **PowerShell使用**: コマンドプロンプトよりPowerShellを推奨
4. **定期的なChrome再起動**: 長時間使用時は "Chrome再起動" 機能を活用

## 🔗 関連ドキュメント

- [基本セットアップ](README.md)
- [トラブルシューティング](LLM_AS_OPTION.prompt.md)
- [開発者向けガイド](IMPLEMENTATION_SUMMARY.md)

---

## 📞 サポート

Windows固有の問題が発生した場合は、以下の情報と共にIssueを作成してください：

```powershell
# 環境情報収集
echo "Windows Version: $(Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion)"
echo "Python Version: $(python --version)"
echo "Chrome Path: $(Get-Command chrome -ErrorAction SilentlyContinue | Select-Object Source)"
pip list | Select-String "gradio|playwright"
```
