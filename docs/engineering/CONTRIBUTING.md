# Contributing Guidelines

最終更新: 2025-08-26

## 概要

2bykilt プロジェクトへの貢献に関するガイドラインです。効率的な開発プロセスと高品質なコードベースの維持を目的としています。

## 開発プロセス

### 1. Issue ベース開発

- すべての変更は Issue から開始
- Issue には Priority (P0-P3) と Size (S/M/L) を必須設定
- 依存関係を `docs/roadmap/ISSUE_DEPENDENCIES.yml` で管理 (変更時は `ROADMAP.md` Section K の Pre-PR チェック必須)

### 2. Branch 戦略

```bash
# Feature branch 命名規則
feature/issue-XX-brief-description
hotfix/critical-bug-description
docs/documentation-update
```

### 3. Pull Request プロセス

1. 依存関係検証 (`validate_dependencies.py` / ROADMAP Section K 手順)
2. 最小限の変更実装
3. テスト実行と成功確認
4. 依存生成物再生成 (graph / dashboard / queue) & 検証 (idempotent 確認)
5. PR 作成（テンプレート使用: Docs Updated / Validation / Idempotent 記載）
6. レビューと承認
7. マージ後: Roadmap 進捗と同期差分確認

## コード標準

### 1. Python コード

```python
# Type hints 必須
def process_data(input_data: List[Dict[str, Any]]) -> Optional[ProcessedData]:
    """
    データ処理関数
    
    Args:
        input_data: 入力データリスト
        
    Returns:
        処理済みデータ、エラー時は None
        
    Raises:
        ValidationError: 入力データが不正な場合
    """
    pass

# Logging 標準
import logging
logger = logging.getLogger(__name__)

logger.info("Processing started", extra={
    "component": "module_name",
    "action": "process_start",
    "count": len(input_data)
})
```

### 2. 設定管理

- Feature flags 使用推奨
- 環境変数でのカスタマイズ対応
- デフォルト値の明示

### 3. エラーハンドリング

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error("Operation failed", extra={
        "error": str(e),
        "context": "specific_operation"
    })
    raise ProcessingError(f"Failed to process: {e}") from e
```

## テスト要件

### 1. テスト種別

- Unit tests: 個別関数/クラス
- Integration tests: コンポーネント間連携
- E2E tests: 全体フロー

### 2. テスト実行

```bash
# ローカルテスト実行
python -m pytest tests/ -v --cov=src

# 特定のマーカーのみ
python -m pytest tests/ -m "unit" -v

# カバレッジレポート
python -m pytest tests/ --cov=src --cov-report=html
```

補足: インポートパスの設定は `tests/conftest.py` が自動で行います。標準ではリポジトリルートと `src/` を `sys.path` に追加します。非標準レイアウトで実行する場合は、環境変数 `BYKILT_ROOT` にプロジェクトのルートパスを設定してください。

### 3. テスト品質

- Edge case の考慮
- Mock の適切な使用
- テストデータの管理

## ドキュメント標準

### 1. Markdown 規則

- 見出しレベルの適切な使用
- リンク切れの回避
- 多言語対応（日英混在OK）

### 2. 必須ドキュメント更新

- API 変更時: インターフェース仕様
- 設定追加時: CONFIG_SCHEMA.md
- Flag 追加時: FLAGS.md
- ログ変更時: LOGGING_GUIDE.md

### 3. バージョン管理

- 改訂履歴の記載
- 最終更新日の設定
- 互換性情報の記載

## Security 要件

### 1. Secret 管理

```python
# ❌ NG: Hardcode
API_KEY = "sk-1234567890abcdef"

# ✅ OK: Environment variable
import os
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable required")
```

### 2. Input validation
 
```python
from pathlib import Path

def safe_file_access(file_path: str) -> Path:
    """安全なファイルアクセス"""
    path = Path(file_path).resolve()
    if not str(path).startswith("/allowed/directory"):
        raise ValueError("Path traversal attempt detected")
    return path
```

### 3. Dependency management

- 定期的な依存関係更新
- 脆弱性スキャンの実行
- ライセンス確認

## パフォーマンス要件

### 1. 計測とモニタリング
 
```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info("Function completed", extra={
                "function": func.__name__,
                "duration": duration,
                "success": True
            })
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Function failed", extra={
                "function": func.__name__,
                "duration": duration,
                "error": str(e)
            })
            raise
    return wrapper
```

### 2. リソース使用量

- メモリ使用量の監視
- CPU 使用率の考慮
- I/O 操作の最適化

## CI/CD 連携

### 1. 自動チェック

- Lint (flake8, black)
- Type check (mypy)
- Security scan (bandit)
- Dependency check (pip-audit)

### 2. 品質ゲート

- テスト成功率 >= 95%
- Coverage >= 80%
- Security scan クリア
- Performance regression なし

### 3. Pytest / CI 実行統一 (追加ガイド)

以下変更を含む PR では必ずチェックしてください:

- [ ] `pytest.ini` / `pyproject.toml` で test 設定を移動・改名した → `.github/workflows/` で旧パス参照が残っていないか `grep -R "tests/pytest.ini" .` で確認
- [ ] CI / ローカルで pytest 実行コマンドを分岐させていない (`scripts/ci_pytest.sh` を利用)
- [ ] 新しいマーカーを追加した場合は `pytest.ini` の markers セクションに追記
- [ ] `ci_safe` マーカー対象に含める/含めない理由を PR 説明に 1 行記載
- [ ] 旧ファイル削除後に残存パス参照で失敗しないか `scripts/ci_pytest.sh full` を一度実行

## Issue ラベル管理

### 1. 必須ラベル

- Priority: P0/P1/P2/P3
- Size: S/M/L
- Type: feat/bug/docs/chore
- Area: config/security/logging/etc

### 2. 状態管理

- ready: 実装可能
- blocked: 依存関係待ち
- in-progress: 実装中
- needs-review: レビュー待ち

## コミットメッセージ規則

```bash
# Format
<type>(<scope>): <description>

# Examples
feat(config): add feature flag framework
fix(logging): resolve log format issue
docs(roadmap): update dependency graph
test(artifacts): add integration tests
```

## レビュープロセス

### 1. レビュー観点

- 要件充足
- コード品質
- テスト充足性
- ドキュメント更新
- セキュリティ考慮

### 2. レビュー者責任

- 24時間以内の初回レスポンス
- 建設的なフィードバック
- Alternative 案の提示

## トラブルシューティング

### 1. 依存関係問題
 
```bash
# 依存関係 & 孤立 / high_risk / cycles 検証
python scripts/validate_dependencies.py docs/roadmap/ISSUE_DEPENDENCIES.yml

# 厳格 orphan モード (任意)
python scripts/validate_dependencies.py --orphan-mode exact docs/roadmap/ISSUE_DEPENDENCIES.yml
```

### 2. テスト失敗
 
```bash
# 詳細ログ出力
python -m pytest tests/ -v -s --tb=long

# 特定テストのみ実行
python -m pytest tests/test_specific.py::test_function -v
```

### 3. パフォーマンス問題
 
```bash
# プロファイリング実行
python -m cProfile -o profile.stats main.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"
```

## 品質指標

### 1. 開発効率

- Issue 完了サイクル時間
- PR マージまでの時間
- リワーク率

### 2. 品質指標

- バグ発生率
- テストカバレッジ
- ドキュメント同期率

## 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-08-26 | 初期ドラフト作成 | Copilot Agent |
| 1.1.0 | 2025-09-06 | CI pytest 実行統一/ドリフト防止チェックリスト追加 | Copilot Agent |

---

このガイドラインに従って、効率的で高品質な開発を進めてください。
