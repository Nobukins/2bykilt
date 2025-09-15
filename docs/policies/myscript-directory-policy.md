# myscript ディレクトリ配置規約（初稿）

Status: Draft

Updated: 2025-09-15

Owner: Runner/Tooling WG

Related: #50, #193

※ #193: myscript ディレクトリ配下の生成物配置に関する議論・要件整理のIssue。

## 目的

- `myscript/` 配下の役割と配置ルールを明確化し、実行スクリプトと生成物の分離、参照パスの一貫性、CI/ドキュメントとの整合を確保する。

## スコープ

- In:
  - `myscript/` 配下の構成・命名・責務分担
  - 生成物（録画、マニフェスト、ログなど）の出力先規約
  - パス/環境変数（RECORDING_PATH, BASE_DIR）取り扱い
- Out:
  - ランタイム/機能仕様の詳細（別ドキュメント）

## ディレクトリ構成（提案）

```text
myscript/
  bin/              # 実行可能スクリプト（エントリポイント）
  templates/        # スクリプトテンプレートやサンプル
  helpers/          # ヘルパーモジュール（再利用可能）
  README.md         # 利用方法/規約の要約
```

- 生成物（録画/マニフェスト/一時ファイル）は `myscript/` 直下に置かない。
- 生成物は原則以下のいずれかへ出力する。
  - アーティファクト: `artifacts/<flow or task>/...`
  - 一時ファイル: `tmp/<task>/...`

## 出力先と命名規則

- 録画（動画）: `artifacts/<task>/Tab-XX-<name>.webm`（Tab-XX は 2 桁ゼロ詰め）
- マニフェスト: `artifacts/<task>/tab_index_manifest.json`
- ログ: `artifacts/<task>/logs/` または `tmp/<task>/logs/`

## 環境変数/設定

- RECORDING_PATH: 録画/マニフェストの出力先ディレクトリ（必須）
- BASE_DIR: 相対基点ディレクトリ。未指定時はリポジトリルートを推奨
- 既定のフォールバックは行わず、未設定時は明示エラーを推奨（CIで検出容易化）

## パス参照の原則

- スクリプト内のファイル参照は `BASE_DIR` or `Path(__file__).parents[n]` による明示基点指定
- 文字列連結ではなく `pathlib.Path` を使用
- `RECORDING_PATH` は存在チェックと作成（mkdir -p 相当）を必ず行う

## 依存関係

- Phase2-06 成果物（録画パス統一、Tab-XX リネーム、マニフェスト生成）を前提

## 受け入れ基準

- `myscript/` の構成・出力先・命名・環境変数の規約が本ドキュメントに記載される
- 代表スクリプトが規約に準拠して動作（録画/マニフェストが規定パスに生成）
- CI で当該パスを前提とした収集が成功する

## 移行ガイド（概要）

1. 既存スクリプトを `myscript/bin/` に移動、相対参照を `BASE_DIR` ベースに修正
2. 出力を `RECORDING_PATH` に集約し、`Tab-XX` リネーム/マニフェスト生成に対応
3. CI ワークフローの収集パスを `artifacts/**` に統一
4. README/チュートリアルの参照を更新

## 今後の拡張（任意）

- 生成物の TTL とクリーンアップポリシー
- スクリプトの命名規約（動詞-目的-オプションなど）
- Lint/静的検査（Path usage, env var presence）
