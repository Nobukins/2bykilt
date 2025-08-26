# 🎯 2bykilt条件分岐UI実装の最適化プロンプトテンプレート

## 📋 概要

このドキュメントは、今回実装した「ENABLE_LLMによる条件分岐UI」のような複雑な機能を、より効率的に実装するための最適化されたプロンプトテンプレートです。

---

## 🏗️ 最適プロンプト構造

### 1. 初期要求プロンプト

```markdown
## 🎯 機能実装リクエスト

### 📌 実装目標
- Gradio Pythonアプリケーションで条件分岐UI実装
- 環境変数ENABLE_LLMによる2つのUIモード切り替え
- Windows Server 2022 (日本語)環境での動作保証

### 🎛️ 要求仕様
- **ENABLE_LLM=true**: フル機能（Gradio Video再生コンポーネント付き）
- **ENABLE_LLM=false**: 軽量版（HTML fallback UI）
- 分離された仮想環境での検証
- エラーハンドリングとWindows対応の強化

### 📁 関連ファイル
- メインアプリ: `bykilt.py`
- 環境設定: `.env`
- 依存関係: `requirements.txt`
- 録画ディレクトリ: `tmp/record_videos/`

### 🌍 環境要件
- OS: Windows Server 2022 (日本語)
- Shell: PowerShell
- Python: 3.11+
- UI Framework: Gradio 5.x
```

### 2. コンテキスト提供テンプレート

```markdown
## 📂 事前コンテキスト
以下のファイルを先読みして実装の理解を深めてください：

1. **アプリケーション構造**: `bykilt.py` (L1-100, L1280-1500)
2. **現在の設定**: `.env` ファイル全体
3. **依存関係**: `requirements.txt` の主要モジュール確認
4. **既存UI**: Recordingsタブの現在の実装

## 🔍 重要チェックポイント
- [ ] 既存のLLMモジュールimport構造
- [ ] Gradio Video コンポーネントの利用状況
- [ ] 条件分岐の現在の実装有無
- [ ] エラーハンドリングの現状
```

### 3. 段階的実装プロンプト

```markdown
## 🚀 段階的実装アプローチ

### Phase 1: 分析・調査
1. 現在のRecordingsタブ実装を分析
2. ENABLE_LLM環境変数の読み込み状況確認
3. Gradio Videoコンポーネントの動作検証
4. エラーログから問題点特定

### Phase 2: 環境準備
1. `.env`ファイルでENABLE_LLM設定
2. 新しい仮想環境 `.venv-full` 作成
3. フルrequirements.txtインストール
4. 録画ディレクトリの確認・作成

### Phase 3: 条件分岐ロジック実装
1. LLMモジュール条件付きimport
2. UI条件分岐ロジックの追加
3. fallback HTML UI の実装
4. エラーハンドリング強化

### Phase 4: 検証・テスト
1. ENABLE_LLM=falseモードテスト
2. ENABLE_LLM=trueモードテスト（新環境）
3. 動画再生機能の確認
4. エラーレス動作の検証
```

---

## 🔧 実装時のベストプラクティス

### 1. ファイル編集アプローチ

```markdown
## 📝 効率的なファイル編集戦略

### 優先順位
1. **読み込み**: 関連セクションを大きめのチャンクで読み取り
2. **分析**: 既存コードの構造と依存関係を理解
3. **計画**: 変更点を事前に整理
4. **実装**: 小さな変更単位で段階的に実行
5. **検証**: 各段階でエラーチェック

### コード編集のコツ
- `replace_string_in_file`: 小さな変更、確実な置換
- `insert_edit_into_file`: 大きな追加、新機能実装
- 変更前後5-10行のコンテキスト必須
- 一度に1ファイルずつ編集
```

### 2. エラーハンドリング戦略

```markdown
## 🛡️ エラー対応のベストプラクティス

### Windows固有対応
- エンコーディング問題 (UTF-8, CP932, Shift_JIS)
- パス区切り文字 (Pathlib使用推奨)
- PowerShell制限 (&&演算子回避)
- 権限問題 (管理者実行確認)

### Gradioスキーマエラー対応
- Video componentの条件付き利用
- 適切なfallback UI提供
- try-except での安全な初期化
- ログ出力でデバッグ支援
```

### 3. 環境管理テンプレート

```markdown
## 🐍 仮想環境管理戦略

### 複数環境並行運用
- `.venv-minimal`: 軽量版 (ENABLE_LLM=false)
- `.venv-full`: フル版 (ENABLE_LLM=true)
- 明確な環境切り替え手順
- 依存関係の分離管理

### 検証プロセス
1. 環境作成とアクティベート確認
2. 必要モジュールの正常インストール確認
3. アプリ起動とポート確認
4. ブラウザでのUI動作確認
5. 条件分岐動作の検証
```

---

## 📊 効率性向上のポイント

### 1. 事前準備で時間短縮

```markdown
## ⚡ 効率化のためのコンテキスト情報

### 必要最小限の情報を先に収集
- プロジェクト構造の把握
- 既存実装の理解
- エラーログの事前確認
- 関連ファイルの特定

### 優先順位をつけた実装順序
1. **Critical**: 基本動作の確保
2. **High**: 条件分岐ロジック
3. **Medium**: UI改善
4. **Low**: 追加機能
```

### 2. 並行処理可能なタスク

```markdown
## 🔄 並行実行可能な作業

### 同時進行できるタスク
- ファイル読み取り (複数ファイルの並行read_file)
- 環境準備 (仮想環境作成中に他分析)
- 検証プロセス (異なるポートでの並行テスト)

### 順次実行が必要なタスク  
- ファイル編集 (競合回避)
- 環境のアクティベート
- アプリケーション起動
```

---

## 🎯 成功パターンのテンプレート

### 1. 高効率プロンプトの例

```markdown
I need to implement conditional UI switching in a Gradio Python application based on ENABLE_LLM environment variable. The application should provide:

1. **ENABLE_LLM=true**: Full-featured Video playback UI with Gradio Video component
2. **ENABLE_LLM=false**: Lightweight HTML-based fallback UI

**Environment**: Windows Server 2022 (Japanese), PowerShell
**Files to modify**: `bykilt.py` (Recordings tab section), `.env`
**Testing requirement**: Separate virtual environments for each mode

Please start by analyzing the current implementation of the Recordings tab in `bykilt.py` around lines 1280-1400, then implement the conditional logic step by step.
```

### 2. コンテキスト最適化の例

```markdown
Before implementing, please:
1. Read the current Recordings tab implementation in `bykilt.py`
2. Check the current ENABLE_LLM handling in the file
3. Verify the .env file structure
4. Identify any existing Gradio Video component usage

This will help you understand the current architecture and plan the implementation efficiently.
```

---

## 📈 品質保証チェックリスト

### 1. 実装完了の確認項目

- [ ] **環境分離**: 複数の仮想環境で正常動作
- [ ] **条件分岐**: ENABLE_LLM true/false両方で期待通り動作
- [ ] **UI機能**: 動画再生またはfallback表示が正常
- [ ] **エラーハンドリング**: Windows環境での安定動作
- [ ] **ログ出力**: 適切なデバッグ情報の提供

### 2. パフォーマンス検証

- [ ] **起動時間**: 適切な初期化時間
- [ ] **メモリ使用量**: 軽量版での効果確認
- [ ] **応答速度**: UI操作の快適性
- [ ] **リソース管理**: 適切なcleanup処理

### 3. 保守性の確保

- [ ] **コード可読性**: 明確な条件分岐ロジック
- [ ] **ドキュメント化**: 実装の記録
- [ ] **エラーログ**: 問題特定の容易さ
- [ ] **設定管理**: 環境変数での制御

---

## 🔮 さらなる効率化のヒント

### 1. プロンプトの改善点

- **具体性の向上**: ファイル名、行番号、関数名を明示
- **段階的アプローチ**: 複雑なタスクを小分け
- **コンテキスト活用**: 既存実装の理解を前提とした指示
- **検証組み込み**: 実装と同時にテスト指示

### 2. ツール活用の最適化

- **read_file**: 大きなチャンクでの効率的読み取り
- **semantic_search**: 関連コードの迅速特定
- **grep_search**: 特定パターンの一括検索
- **run_in_terminal**: 並行実行可能なコマンド特定

### 3. エラー回避戦略

- **Windows対応**: エンコーディング、パス、権限の事前考慮
- **Gradio互換性**: バージョン固有問題の事前調査
- **仮想環境**: 依存関係分離による安定性確保
- **段階的検証**: 各段階での動作確認

---

## 📝 実装後の改善サイクル

### 1. 振り返り分析

- 実装にかかった時間の分析
- エラー発生箇所と解決方法の記録
- 効果的だったアプローチの特定
- 次回改善できるポイントの洗い出し

### 2. テンプレート更新

- 成功パターンのテンプレート化
- エラーパターンの回避策追加
- 新しい効率化手法の組み込み
- ドキュメントの継続的改善

---

*このテンプレートは、実際の実装経験を基に作成された実践的なガイドです。プロジェクトの特性に応じてカスタマイズしてご利用ください。*
