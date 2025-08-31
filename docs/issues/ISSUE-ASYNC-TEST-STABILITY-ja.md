# 課題: 非同期 / ブラウザ統合テスト安定化とスコープ分離

識別子: (新規) Async Test Stability （本Issue作成後に番号付与）  
ステータス: Open  
優先度: Medium（設計PRのマージは阻害しないが将来の信頼性確保に必須）  
Wave: A2 (Issue #31 後続)  
関連PR: #80 (Logging Design)  

## 背景 / 概要

Full Test Suite 実行で、Logging Design (Issue #31) と無関係な多数の失敗が発生。主因は非同期イベントループ管理とブラウザ／プロファイル依存テストの環境前提不足。設計フェーズの進行を阻害しないよう、ロギング設計PRでは最小契約テストのみCI対象とし、安定化を本Issueで包括的に扱う。

## 現状の主な不安定要素

- 反復パターン: `RuntimeError: This event loop is already running / Cannot close a running event loop / Runner is closed`
- ブラウザ統合/Edge/プロフィール関連テスト: 実ブラウザ & プロファイルパス存在を前提
- `FileNotFoundError` / `Invalid SeleniumProfile path` 例外がテスト内で未キャッチ → teardown 連鎖
- `PytestUnhandledCoroutineWarning` / ループクリーンアップ警告: strict モード＋fixture 実装不整合疑い

## 想定原因 (仮説)

1. `pytest-asyncio` の `strict` モードと anyio プラグインの併用でループ多重管理
2. ブラウザ (Edge/Chrome) 実環境存在チェック不足による強制失敗
3. プロファイル用一時ディレクトリ生成不備とパス検証のタイミングずれ
4. 非同期fixtureで明示的 `loop.close()` 相当の処理 or 終了前未キャンセル Task 残存
5. 単一ジョブで高コスト統合テストを全実行 → 診断難度上昇

## 影響

- CI フル実行がノイズ化しMRレビュー速度低下
- 本来の回帰検知能力低下 (false negative / false positive)
- Sonar / カバレッジレポートに無関係失敗が混入

## 本Issueのスコープ

テスト層のレイヤリング確立と非同期/環境依存領域の安定化。機能追加は対象外。ログ実装(#56+) への前提整備を目的とする。

### アウトオブスコープ

- 新たなブラウザ機能実装
- ロギング実装機能 (#56, #57, #58) そのもの
- 既存テストが露見させた本質的プロダクト仕様変更（別Issueで扱う）

## 成果物 (Deliverables)

1. マーカー/レイヤリング設計
   - 追加マーカー: `unit`, `logging_spec`, `integration`, `browser`, `slow` (既存: `ci_safe`, `local_only` 整理)
   - `pytest.ini` の markers 定義更新 + README/CONTRIBUTING 反映
2. CI 分離
   - デフォルト (PR) ジョブ: `unit or logging_spec` + 必要最小 integration smoke (任意)
   - Nightly (任意): full suite (allow-fail→安定後必須化)
3. 条件付き Skip Guard
   - `tests/helpers/env_checks.py`: `has_edge()`, `has_chrome()`, `has_browser_profiles()`
   - `pytest.skip(...)` 理由明示 (例: "edge not installed")
4. 非同期基盤調整
   - `asyncio_mode = auto`（暫定→安定後再評価）
   - すべての async テストへ `@pytest.mark.asyncio` (auto化後も可読性担保)
   - ループ利用 fixture を監査: 未await Task / 未クローズ資源 (browser, webdriver) を安全解放
5. プロファイルテスト改善
   - Factory fixture: ダミープロファイル構造 (必要ディレクトリ/ファイル群) を tempdir に生成
   - パス検証例外をラップしテスト期待値統一
6. 安定化テスト
   - 代表失敗シナリオ再現 → 修正後再実行ログ保存
   - ループ teardown 時の RuntimeWarning が 0 であることを asserts
7. ドキュメント
   - `docs/testing/TEST_STRATEGY.md` 新規 (層・マーカー・CI マトリクス)
   - PR テンプレートへ「テスト層」チェック項目追加（任意）

## 受け入れ基準 (Acceptance Criteria)

- `pytest -m "unit or logging_spec"` がクリーンパス (CI Linux) かつ loop 関連 RuntimeError/Warning 0
- Edge/Chrome 未インストール環境で browser マーカー付テストが Skip としてカウント (Fail 0)
- full suite (開発者環境) 実行で event loop RuntimeError 再発 0
- 新規 `TEST_STRATEGY.md` にテスト層/マーカー/CI 実行ポリシー記載
- Nightly (任意設定時) ジョブログでブラウザ系 skip 理由が可視化

## 実施ステップ (Phased Plan)

| Phase | 内容 | 成功条件 |
|-------|------|----------|
| 1 | マーカー追加 & env_checks 導入 | unit/logging_spec 選択実行成功 |
| 2 | async fixture 監査 & 不要 loop 操作削除 | loop RuntimeError 消失 |
| 3 | プロファイル工場 fixture & 例外整形 | プロファイル関連テスト安定/Skip または Pass |
| 4 | Nightly full suite workflow 追加 | Nightly 成果物 (レポート) 生成 |
| 5 | 文書化 & テンプレ更新 | TEST_STRATEGY.md 提出 |
| 6 | 総合安定確認 | Acceptance Criteria 全充足 |

## リスクと軽減策

| リスク | 説明 | 軽減策 |
|--------|------|--------|
| 過度な Skip | 観測範囲低下 | Nightly full, 週次レビュー |
| Marker 乱用 | 意図的誤分類 | コードレビューでマーカー差分確認 |
| 非同期デッドロック | 修正中に新たなハング | タイムアウト付き fixture / anyio fail-fast |
| ブラウザ環境差異 | CI/ローカル挙動ギャップ | env_checks + ログ出力に前提明示 |

## 計測/可視化 (任意強化)

- pytest summary にマーカー別件数出力 (custom plugin 小)
- Nightly で skip 理由トップ3 集計コメント化

## 参考

- PR #80 (Logging design contract isolation)
- 現行 `tests/pytest.ini` (asyncio_mode=auto) 暫定変更

---
(End of Japanese Issue Draft)
