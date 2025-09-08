# Artifact Manifest v2 (Issue #35)

最終更新: 2025-09-03

## 概要

Wave A3 の範囲では video / screenshot / element_capture の 3 種を対象に **最小スキーマ** を確定し、後続 (#36 一覧 API / #37 保持期間 / #38 回帰テスト / #58 Metrics) の基盤とする。拡張的大規模フィールド（checksums / retention / tags 等）は v2 スコープ外（将来 v3 予定）。

## スコープ内 Artifact 種別 (v2)

| type | ファイル配置 (相対) | meta 例 | 備考 |
|------|----------------------|---------|------|
| video | videos/*.mp4(webm) | original_ext / final_ext / transcoded / register_duration_ms | 変換は ffmpeg 存在時 (#30) |
| screenshot | screenshots/*.png | format: png | 将来 user_named (#87) 追加予定 |
| screenshot (duplicate copy) | screenshots/`<prefix>`_`<ts>`.png | format: png | Flag `artifacts.screenshot.user_named_copy_enabled` (Issue #87) により生成 / OFF で無効 |
| element_capture | elements/*.json | selector: \<CSS\> | JSON 本体に text/value/captured_at |

## JSON 構造 (最小)

```jsonc
{
    "schema": "artifact-manifest-v2",
    "run_id": "20250903_123456_ABC",
    "generated_at": "2025-09-03T12:34:56.789012Z",
    "artifacts": [
        { "type": "video", "path": "artifacts/runs/.../videos/run_0001.mp4", "created_at": "...", "size": 1234, "meta": {"original_ext": ".webm", "final_ext": ".mp4", "transcoded": true, "register_duration_ms": 110} },
        { "type": "screenshot", "path": "artifacts/runs/.../screenshots/screenshot_20250903_123500.png", "created_at": "...", "size": 45678, "meta": {"format": "png"} },
        { "type": "element_capture", "path": "artifacts/runs/.../elements/element_20250903_123501123456.json", "created_at": "...", "size": 234, "meta": {"selector": "#login"} }
    ]
}
```

### エントリフィールド

| フィールド | 型 | 説明 |
|------------|----|------|
| type | string | 種別 (video/screenshot/element_capture) |
| path | string | POSIX 相対パス (安定参照用) |
| created_at | string(ISO8601 UTC) | 生成時刻 |
| size | number/null | バイトサイズ (取得不能時 null) |
| meta | object/null | 種別固有メタ (拡張領域) |

## Flag 動作

`artifacts.enable_manifest_v2` = false の場合は **manifest_v2.json を生成せず** 既存 capture は通常出力のみ。

## 一覧 API (Issue #36)

エンドポイント: `GET /api/artifacts`

クエリパラメータ:

- `limit` (int, 任意, default=10): 取得対象 run manifests の走査上限 (最新 run から降順)。
- `type` (string, 任意): `video` / `screenshot` / `element_capture` にフィルタ。

レスポンス例:

```jsonc
{
    "items": [
        {"run_id": "20250903T101010-abcd01", "type": "screenshot", "path": "artifacts/runs/.../screenshots/xxx.png", "size": 4567, "created_at": "...", "meta": {"format": "png"}},
        {"run_id": "20250903T101010-abcd01", "type": "element_capture", "path": ".../elements/element_...json", "size": 234, "created_at": "...", "meta": {"selector": "#login"}}
    ],
    "count": 2
}
```

実装メモ:

- 各 run の `manifest_v2.json` を上限 `limit` 件まで読み込み、`artifacts[]` をフラット化し `run_id` 埋め込み。
- 将来的な pagination / cursor は v3 拡張 (Issue #38 regression suite 運用状況見ながら検討)。
- `type` フィルタはメモリ内フィルタ (現状件数小規模想定)。

### 将来拡張 TODO (リンク)

| 項目 | Issue | メモ |
|------|-------|------|
| video retention ポリシ metadata 表示 | #37 | video entry meta に retention_days 追加 (実装済) |
| metrics export (カウント/バイト) | #58 | list API に aggregated counters オプション追加 (e.g. `summary`) |
| pagination / cursor | #38 | regression suite 運用で必要性確認後 v3 |
| screenshot user_defined 名称 | #87 | prefix に user 指定名許可 (重複保存制御と組み合わせ) |
| screenshot 例外種別ログ | #88 | manifest 失敗 WARN を細分 (特定例外 → info/skip) |
| screenshot ログイベント拡張 | #89 | metrics 連携用 event フィールド (latency / size) |

> 上記 TODO は PR #95 から参照されるフォローアップ計画。個別 Issue 側で Acceptance Criteria 詳細化予定。

## 将来拡張 (v3 候補)

- checksums / hash integrity
- retention_days per entry (現状は #37 で video のみ time-based 削除)
- tags, related_artifacts, logical groups
- metrics export hooks (entry counts / bytes) (#58)

## テスト (最小)

1. Flag ON: 各 API 呼び出し後 artifacts 配列件数増加
2. Flag OFF: manifest_v2.json 不在 or 未更新
3. element_capture JSON 実体と manifest entry path 整合
4. video transcode (条件成立時) meta.transcoded true

---

改訂履歴:

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 2.0.0 | 2025-08-26 | 初期包括ドラフト | Copilot Agent |
| 2.0.1 | 2025-09-03 | Issue #35 最小スキーマ定義へスコープ縮小 / 過剰フィールド分離 | Copilot Agent |
| 2.0.2 | 2025-09-03 | Issue #36 一覧 API 仕様/レスポンス記述 & 将来拡張 TODO 追加 (links: #37 #58 #38 #87 #88 #89) | Copilot Agent |
| 2.0.3 | 2025-09-03 | Issue #87 重複ユーザー向けスクリーンショットコピー行追加 / Flag 説明明記 | Copilot Agent |
| 2.0.4 | 2025-09-03 | Issue #37 video retention_days meta 追加 (video エントリ) | Copilot Agent |
