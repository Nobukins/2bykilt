# ローカルテスト実行ガイド

このドキュメントは、ローカル環境でテストを実行するための手順書です。CI-safe な軽量検証から、実ブラウザを伴うローカル限定（local_only）テスト、そしてフルテストまでをカバーします。

## 前提条件

- OS: macOS / Linux / Windows（PowerShell でも可、以下は zsh 前提）
- Python: 3.12 系（本リポジトリは 3.12 で検証）
- 仮想環境: `venv/`（既存）、または新規作成
- 依存関係: `requirements.txt`（フル） もしくは `requirements-minimal.txt`（軽量）
- ブラウザ自動化: Playwright ブラウザをローカルで使用する場合はインストールが必要

## 環境準備

1) 仮想環境の作成（未作成の場合）
```zsh
python3.12 -m venv venv
```

2) 仮想環境の有効化
```zsh
source venv/bin/activate
```

3) 依存関係のインストール
- フルテスト（推奨: まずはフルに統一）
```zsh
python -m pip install -U pip
pip install -r requirements.txt
```
- 軽量セット（CI-safe 中心で十分な場合）
```zsh
python -m pip install -U pip
pip install -r requirements-minimal.txt
```

4) Playwright ブラウザのインストール（実ブラウザを使うテスト／local_only 実行時に必要）
```zsh
python -m playwright install
```

## 実行パターン

以下のコマンドは、すべてプロジェクトのルート（本ファイルがあるリポジトリ直下）で実行します。

### 1) CI-safe のみ（最速・外部依存なし）
```zsh
python -m pytest -q -m ci_safe
```
- tests/pytest.ini を明示する場合:
```zsh
python -m pytest -q -m ci_safe -c tests/pytest.ini
```

### 2) local_only のみ（ローカル検証。実ブラウザ・環境依存あり）
```zsh
python -m pytest -q -m local_only
```
- 実行前に `python -m playwright install` 済みであること

### 3) フルテスト（すべてのテストを実行）
```zsh
python -m pytest -q
```
- pytest.ini を明示したい場合:
```zsh
python -m pytest -q -c tests/pytest.ini
```

### 4) カバレッジ付き実行（XML/HTML）
- XML（CI と同等の成果物）
```zsh
coverage run -m pytest -c tests/pytest.ini
coverage xml -i -o coverage.xml
```
- 端末レポート + HTML レポート
```zsh
coverage run -m pytest -c tests/pytest.ini
coverage report -m
coverage html -d htmlcov
```

### 5) 一部だけ実行（キーワード指定・詳細表示）
```zsh
python -m pytest -q -k "option_availability"
python -m pytest -vv -k "test_ci_smoke_report"
```

## GUI でのインタラクティブ検証

Option Availability タブから、アクション読み込み・録画パス作成・安全な初期化プローブを手動確認できます。
```zsh
python bykilt.py
```
- ブラウザで http://localhost:7860 を開き、「Option Availability」タブへ

## トラブルシューティング

- pytest が見つからない
  - 仮想環境が有効化されていない可能性があります。`source venv/bin/activate` 実行後に `python -m pytest` で再実行してください。
- Unknown pytest.mark.ci_safe の警告
  - `-c tests/pytest.ini` を付けて pytest を実行してください（マーカー登録を読ませるため）。
- Playwright 関連のエラー（ブラウザ未インストール）
  - `python -m playwright install` を実行してください。
- 外部ブラウザが立ち上がらない／CI では失敗する
  - 実ブラウザを伴うテストは `local_only` に限定してください。CI は `-m ci_safe` のみで実行されます。
- Websockets や Deprecation の警告
  - 既知の非機能的警告です。必要に応じて pytest の `-W` オプションで抑制可能です。

## 補足

- サブプロセス経由の Python 実行は、PATH に依存せず常に現在のインタプリタ（`sys.executable`）を用いるよう統一済みです。
- CI（GitHub Actions）では `-m ci_safe` のみを実行して coverage.xml を生成するよう設定されています（`.github/workflows/security-ci.yml`）。ローカルでは用途に応じて上記パターンを選択してください。

---

最短ルート（おすすめ）
```zsh
source venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
python -m playwright install  # 実ブラウザ系も確認したい場合
python -m pytest -q           # まずは全体のスモーク
python -m pytest -q -m local_only  # 実ブラウザを使うものだけ追加検証
```
