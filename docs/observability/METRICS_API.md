# Run Metrics API (Issue #59)

最終更新: 2025-09-13

FastAPI ベースのメトリクス API を提供します。既存の `src/metrics` 基盤の上に、計測済みシリーズの列挙・値取得・要約統計を返すエンドポイントを追加しました。

## エンドポイント

- GET `/api/metrics/series`  
  収集されているメトリクスシリーズ名を配列で返します。

- GET `/api/metrics/series/{name}`  
  指定シリーズの生データを JSON で返します。`?tag=key=value` でタグフィルタが可能。

- GET `/api/metrics/series/{name}/summary`  
  指定シリーズの要約統計（min/max/avg/p50/p90/p95/p99）。`?since_seconds=3600` で最近1時間に限定、`?tag=key=value` でタグフィルタ可能。

## 実装場所

- ルーター: `src/api/metrics_router.py`
- 集計ヘルパー: `src/metrics/aggregator.py`
- アプリ組み込み: `src/api/app.py` (`app.include_router(metrics_router)`)

## 注意事項

- COUNTER は値列をイベント扱いとして count を返します（min/max/avg も参考値として算出）。
- JSON/CSV エクスポートは既存の `MetricsCollector.export_to_json/csv` を利用してください。
