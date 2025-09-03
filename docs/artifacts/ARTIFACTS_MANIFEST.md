# Artifact Manifest v2 (Issue #35)

最終更新: 2025-09-03

## 概要

Wave A3 の範囲では video / screenshot / element_capture の 3 種を対象に **最小スキーマ** を確定し、後続 (#36 一覧 API / #37 保持期間 / #38 回帰テスト / #58 Metrics) の基盤とする。拡張的大規模フィールド（checksums / retention / tags 等）は v2 スコープ外（将来 v3 予定）。

## スコープ内 Artifact 種別 (v2)

| type | ファイル配置 (相対) | meta 例 | 備考 |
|------|----------------------|---------|------|
| video | videos/*.mp4(webm) | original_ext / final_ext / transcoded / register_duration_ms | 変換は ffmpeg 存在時 (#30) |
| screenshot | screenshots/*.png | format: png | 将来 user_named (#87) 追加予定 |
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
