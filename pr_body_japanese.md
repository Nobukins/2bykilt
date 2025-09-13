Issue #59: Run Metrics API の実装

## このPRの内容

### 新しいAPIエンドポイント
- **GET /api/metrics/series**: 利用可能なメトリクス系列名のリストを取得
- **GET /api/metrics/series/{name}**: 特定の系列のメトリクス値を取得（オプションのフィルタリング対応）
  - クエリパラメータ: `tag_filter` (単一のkey=valueペア), `since_seconds` (整数)
- **GET /api/metrics/series/{name}/summary**: メトリクス系列の統計サマリーを取得
  - 返却値: min, max, avg, p50, p90, p95, p99 パーセンタイル

### コア実装
- **src/metrics/aggregator.py**: numpyを使用したパーセンタイル計算を含む `compute_summary()` メソッドを追加
- **src/api/metrics_router.py**: エンドポイント実装を含む新しいFastAPIルーター
  - 単一タグフィルタのパース用ヘルパー関数 `_parse_tag_filter()`
  - 無効な系列名や不正なフィルタに対するエラーハンドリング
- **src/api/app.py**: メトリクスルーターをメインFastAPIアプリケーションに統合

### テストとドキュメント
- **tests/api/test_metrics_api.py**: 全エンドポイントをカバーする包括的なテストスイート
  - 系列リスト取得、フィルタ付き値取得、サマリー計算のテスト
  - FastAPI TestClientを使用した統合テスト
- **docs/observability/METRICS_API.md**: 完全なAPIドキュメント
  - エンドポイント仕様、リクエスト/レスポンス例、エラーコード
  - 現在の制限事項（単一タグフィルタ、ページネーションなし）

### 依存関係と設定
- 新しい外部依存関係は追加せず
- `docs/roadmap/ISSUE_DEPENDENCIES.yml` を更新して#59をin-progressにマーク
- すべての変更は後方互換性あり

## チェック項目

### 依存関係検証
- [x] `requirements.txt` または `pyproject.toml` に新しい依存関係を追加せず
- [x] `docs/roadmap/ISSUE_DEPENDENCIES.yml` を正しく更新（#59をin-progressにマーク）
- [x] 依存関係グラフ検証に合格（`scripts/validate_dependencies.py`）

### テスト
- [x] ユニットテストを追加し、ローカルで合格（`pytest tests/api/test_metrics_api.py`）
- [x] FastAPI TestClientを使用した統合テスト
- [x] テストカバレッジを維持（全体で>80%）
- [x] 既存のテストを破損せず

### 冪等性と安全性
- [x] 生成アーティファクトや永続状態の変更なし
- [x] APIのみの追加で読み取り専用操作
- [x] 安全なロールバック: ルーター統合の削除で変更を元に戻せます
- [x] 既存APIへの破壊的変更なし

### ドキュメント
- [x] APIドキュメントを追加（`docs/observability/METRICS_API.md`）
- [x] 型ヒント付きのインラインコードドキュメント
- [x] エラーハンドリングをドキュメント化
- [x] 現在の制限事項を明確に記載

## フォローアップ

### テスト強化
- エッジケースのテストカバレッジを拡大（空の系列、不正なフィルタ）
- 大規模メトリクスデータセット向けのパフォーマンステスト
- 実際のメトリクス収集ワークフローとの統合テスト

### API改善
- 大規模系列レスポンス向けのページネーション検討
- 複数タグフィルタのサポート（現在は単一key=valueに制限）
- レート制限とキャッシュの考慮
- 非常に大規模なデータセット向けのストリーミングレスポンス

### 監視と可観測性
- API使用状況のメトリクス追加（リクエスト数、レスポンスタイム）
- 将来の変更に向けたAPIバージョニング戦略の検討

## クローズ

- Closes: #59
- Refs: #184 (Phase2-07 トラッカー)

---

*実装はプロジェクトガイドラインに従っています: 最小限の変更、包括的なテスト、完全なドキュメント、依存関係検証。*