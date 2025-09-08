# LOGGING_SPEC (Issue #31 統一ログ設計)

最終更新: 2025-08-30
Status: Draft (Design Only)  / Implements: #31 (prepares #56 / #57 / #58 dependencies)

## 目的

統一された JSON Lines ログフォーマットと最小ロギング基盤仕様を定義する。実装 (#56) の受け入れ基準 / smoke test 条件を明文化し、run_id 基盤 (#32) と密結合する。

## スコープ (Issue #31)

- JSON Lines レコード設計 (必須/任意フィールド)
- 出力ファイル命名規約: `artifacts/runs/<run_id_base>-log/app.log.jsonl` (実装段階で `<run_id_base>-log.jsonl` 直下 か 中間 `-log/` ディレクトリ採用可 / 本設計はサブディレクトリ案を推奨)
- ロガー初期化 API 仕様 (シングルトン / 再初期化禁止 / idempotent)
- 安全性: 例外でプロセスを壊さない / 書き込み失敗は stderr にフォールバック
- 拡張ポイント: rotation (#57), metrics (#58), masking (#60) の挿入 Hook

非スコープ:

- 実際の実装 (#56)
- rotation ポリシー (#57)
- metrics export (#58)
- masking 拡張 (#60)

## JSON Lines レコードフォーマット

| フィールド | 型 | 必須 | 説明 |
|------------|----|------|------|
| ts | string (ISO8601 UTC, `YYYY-MM-DDTHH:MM:SS.sssZ`) | Yes | ログ発生時刻 |
| level | string (DEBUG/INFO/WARNING/ERROR/CRITICAL) | Yes | 標準レベル |
| msg | string | Yes | メインメッセージ (format 済) |
| logger | string | Yes | `__name__` などロガー名 |
| run_id | string | Yes | RunContext.run_id_base |
| component | string | Yes | high-level subsystem (browser, runner, config, agent, logging, artifacts, security, metrics, ui). Naming rule: must match regex `[a-z0-9_]+` (lowercase only). Leading/trailing whitespace, uppercase, hyphen, dot, slash are rejected (ValueError). Rationale: avoid silent normalization masking typos. |
| event | string | Conditional | セマンティックイベント名 (例: `browser.launch`) |
| kwargs | object | Conditional | フォーマット展開補助 / 追加 context (flat or nested) |
| exc | object | Conditional | 例外発生時: {type, message, stack} |
| span | object | Optional | 簡易トレース (parent, id) — future (#58) |
| seq | integer | Optional | 単調増加シーケンス (プロセス内) |
| thread | string | Optional | スレッド名 |
| pid | integer | Optional | プロセス ID |

最小実装 (#56) 要件: ts, level, msg, logger, run_id, component を常に出力。`event` は呼び出し側が渡した場合のみ。

## ログレベル運用ポリシー

- DEBUG: 詳細診断 (デフォルト無効 / FLAG: `logging.debug_enabled` 想定)
- INFO: 標準操作 (デフォルト)
- WARNING: 自動回復可能 or 非推奨
- ERROR: 機能失敗 (処理継続可能)
- CRITICAL: プロセス継続不能 / 主要機能停止

## ファイル配置 & 命名

```text
artifacts/
  runs/
    <run_id_base>-log/              # ディレクトリ (推奨)  *Phase1* (選択肢A)
      app.log.jsonl                 # メインログ
      error.log.jsonl (future)      # レベル別分離案
    <run_id_base>-log.jsonl         # *選択肢B*: 直接ファイル (後方互換 / 単純化)
```
選択肢A を既定方針: 拡張 (複数ファイル/rotation) が容易。Issue #56 では A を採用し、B 互換は不要 (新規機能のため)。

## 初期化 API 仕様

```python
from src.logging.jsonl_logger import JsonlLogger

logger = JsonlLogger.get(component="browser")  # returns standard logging.Logger wrapper
logger.info("Browser launched", extra={"event": "browser.launch", "kwargs": {"headless": True}})
```

### 振る舞い

- `JsonlLogger.get(component)` は同一 component で同一インスタンスを返す
- 内部で `RunContext.get()` を呼び run_id 付与
- 初回呼び出しでファイルハンドラ生成 (ディレクトリ作成含む)
- 2回目以降は再初期化禁止 (idempotent)

### 拡張 Hook

```python
class LogPipelineHook(Protocol):
  def __call__(self, record_dict: dict) -> dict:  # 変更/フィルタ可
    ...
```

- #57 rotation 時: 書き込み前にサイズチェック Hook
- #58 metrics: level カウントインクリメント Hook
- #60 masking: kwargs / msg 内秘密情報マスキング Hook (順序: masking -> metrics -> rotation -> write)

## エラーハンドリング

- 書き込み失敗: 1回 stderr に JSON 文字列を出力し、以後サプレッション (二次障害防止)
- Hook 失敗: 例外握りつぶし + `hook_error` フィールド追加

## 最小実装対象 (Issue #31 出力)

- `src/logging/` パッケージディレクトリ
- `jsonl_logger.py` (設計スケルトン + Docstring + インタフェース + 未実装例外を raise)
- テスト: `tests/logging/test_logging_spec_contract.py` で API 仕様 (型/例外/ディレクトリ生成) のみ検証 (書き込みロジック実装前)
- ドキュメント: 本ファイル + `RUN_CONTEXT_SPEC.md` への cross-link (既存済み) + ROADMAP 進捗更新 (後続 PR)

## Acceptance Criteria (#31)

- [ ] LOGGING_SPEC.md 提出 (本ファイル)
- [ ] JsonlLogger スケルトン追加 (副作用なし / 既存 logger 未破壊)
- [ ] Spec 契約テスト (JSON Lines レコード最低フィールド列挙) がパス (仮実装は raise: NotImplementedError で可)
- [ ] 既存テスト破壊なし (回帰ゼロ)
- [ ] 次 Issue (#56) の実装タスクリスト明確化 (下記)

## 次 Issue (#56) 実装タスクリスト (ドラフト)

1. `JsonlLogger` 内 write 実装 (synchronous append, UTF-8, line-buffered)
2. フィールド整形関数 `_assemble_record(level, msg, component, extra)`
3. Hook チェーン実装 + 登録 API
4. `logger.debug/info/...` ラッパ (標準 logging レベル互換) 実装
5. Smoke test: ファイル 1 行出力 & JSON パース & 必須キー存在
6. Flag: `logging.debug_enabled` (FeatureFlags 経由) で DEBUG 出力切替
7. Rotation 設計インタフェース stub (size threshold, daily)

## リスク & 対応

| リスク | 影響 | 軽減策 |
|--------|------|--------|
| 過剰な初期複雑性 | 実装遅延 | Hook/rotation deferred, skeleton only |
| 既存 app_logger との競合 | 二重出力 | 段階導入: 既存は維持 / 新 JSONL 未接続 |
| パフォーマンス劣化 | 高頻度 I/O | 後続で batch flush / async 検討 (#56 scope外) |

## 用語

- component: 上位サブシステム識別子 (flags, config, runner, browser, agent, artifacts, logging, security, metrics, ui)
- hook: レコード dict を受け取り変更/フィルタする callable

## 参考リンク

- RUN_CONTEXT_SPEC.md (#32)
- ROADMAP.md (Wave A2)

---
