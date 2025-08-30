# Run / Job Context Specification (Issue #32)

最終更新: 2025-08-30

## 目的

Artifacts/Logging/Config/Flags 間で一貫した `run_id_base` を共有し、
観測容易性と後続 (#31 Logging, #56 実装, #58 Metrics) の紐付けを容易化する。

## スコープ (Wave A2 初期)

- 生成タイミング: 初回アクセス時 (`RunContext.get()`)
- フォーマット: `<UTC YYYYMMDDHHMMSS>-<6hex>` (例: `20250830113045-a1b2c3`)
- ディレクトリ命名 (移行段階): `artifacts/runs/<run_id_base>-<component>`
  - `-cfg`  (環境設定アーティファクト)
  - `-flags` (フラグ解決アーティファクト)
- 既存テスト互換のため component suffix 方式を維持 (後で統合検討)

## 非スコープ

- 永続ストア / 複数同時 Run 管理
- ログ出力との統合 (Issue #31 で実施)
- メトリクス / ダッシュボード連動 (#58, #76)

## API

```python
from src.runtime.run_context import RunContext
rc = RunContext.get()
print(rc.run_id_base)
cfg_dir = rc.artifact_dir("cfg")  # Path
```

環境変数 `BYKILT_RUN_ID` 指定時はその値を優先 (再現テスト / 外部オーケストレーション向け)。

## 設計上の考慮

1. Lexicographic Ordering: 先頭が UTC timestamp のため単純ソートで時系列可。
2. 衝突確率: 6 hex (24bit) + 秒精度で実質十分 (追加衝突検出不要と判断)。
3. 後方互換: 既存の `*-cfg`, `*-flags` ディレクトリ構造を維持。
4. 拡張余地: 将来 `artifacts/runs/<run_id_base>/<component>/` へ移行可能。
5. テスト容易性: 固定化したい場合 `BYKILT_RUN_ID` をセット。

## 今後の拡張 (候補)

| Issue | 拡張点 | 備考 |
|-------|--------|------|
| #31 | ログレコードへ run_id 付与 | JSON Lines 共通フィールド |
| #56 | ログファイル命名統一 | `<run_id_base>-log.jsonl` |
| #58 | Metrics ラベル | `run_id` を primary dimension |
| #35 | Artifact Manifest v2 | 各エントリへ run_id 埋込 |

## 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-08-30 | 初版 (RunContext 実装対応) | Copilot Agent |
