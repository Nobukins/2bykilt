# Feature Flags Management

最終更新: 2025-08-26

## 概要

2bykilt プロジェクトにおける Feature Flags の管理とライフサイクルガイドです。安全な機能デプロイと段階的リリースを実現します。

## Feature Flag の目的

### 1. 段階的リリース
- 新機能の限定的公開
- A/B テストの実施
- カナリアリリース対応

### 2. リスク軽減
- 問題発生時の即座な無効化
- ロールバック不要の機能制御
- 影響範囲の限定

### 3. 開発効率向上
- 未完成機能の隠蔽
- 並行開発の支援
- 環境別設定の管理

## Flag 種別

### 1. Release Flags (リリース制御)
```python
# 新機能の段階的公開
ENABLE_NEW_BATCH_UI = {
    "description": "新しいバッチ処理UI",
    "type": "release",
    "default": False,
    "environments": {
        "development": True,
        "staging": True,
        "production": False
    }
}
```

### 2. Experiment Flags (実験・A/B テスト)
```python
# A/B テスト用フラグ
EXPERIMENT_RECORDING_ALGORITHM = {
    "description": "録画アルゴリズムA/Bテスト",
    "type": "experiment", 
    "default": "algorithm_v1",
    "variants": ["algorithm_v1", "algorithm_v2"],
    "rollout_percentage": 50
}
```

### 3. Operational Flags (運用制御)
```python
# システム制御用フラグ
ENABLE_DEBUG_LOGGING = {
    "description": "デバッグログ出力制御",
    "type": "operational",
    "default": False,
    "runtime_configurable": True
}
```

### 4. Permission Flags (権限制御)
```python
# 機能アクセス制御
ENABLE_ADMIN_FEATURES = {
    "description": "管理者機能アクセス",
    "type": "permission",
    "default": False,
    "user_based": True
}
```

## Flag 実装パターン

### 1. 基本的な使用方法
```python
from src.config.feature_flags import FeatureFlags

# Boolean flag
if FeatureFlags.is_enabled("ENABLE_NEW_BATCH_UI"):
    return render_new_batch_ui()
else:
    return render_legacy_batch_ui()

# Multi-variant flag
algorithm = FeatureFlags.get_variant("EXPERIMENT_RECORDING_ALGORITHM")
if algorithm == "algorithm_v2":
    return new_recording_algorithm()
else:
    return legacy_recording_algorithm()
```

### 2. 段階的移行パターン
```python
def process_batch_data(data):
    """段階的な機能移行例"""
    if FeatureFlags.is_enabled("NEW_BATCH_PROCESSOR"):
        try:
            # 新しい処理方式
            result = new_batch_processor(data)
            logger.info("New batch processor used successfully")
            return result
        except Exception as e:
            logger.error(f"New processor failed, falling back: {e}")
            # フォールバック
            if FeatureFlags.is_enabled("ALLOW_PROCESSOR_FALLBACK"):
                return legacy_batch_processor(data)
            raise
    else:
        return legacy_batch_processor(data)
```

### 3. 環境別設定
```python
class FeatureFlagConfig:
    """環境別フラグ設定"""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.flags = self._load_flags()
    
    def _load_flags(self) -> Dict[str, Any]:
        base_flags = {
            "ENABLE_LLM": {
                "development": True,
                "staging": True, 
                "production": False  # Issue #43 対応
            },
            "ENABLE_METRICS_EXPORT": {
                "development": False,
                "staging": True,
                "production": True
            }
        }
        
        return {
            flag: config.get(self.environment, config.get("default", False))
            for flag, config in base_flags.items()
        }
```

## Flag ライフサイクル

### 1. 計画フェーズ
```yaml
# Flag 計画書 (Issue 作成時)
flag_name: ENABLE_NEW_FEATURE
description: "新機能Xの段階的リリース"
category: release
target_issues: ["#64", "#65"]
rollout_plan:
  - phase1: "Development環境で検証"
  - phase2: "Staging環境で統合テスト"
  - phase3: "Production環境で5%ユーザー"
  - phase4: "Production環境で100%ユーザー"
retirement_date: "2025-03-01"
```

### 2. 実装フェーズ
```python
# Flag 定義
FLAGS = {
    "ENABLE_NEW_FEATURE": {
        "description": "新機能Xの段階的リリース",
        "type": "release",
        "default": False,
        "created_date": "2025-08-26",
        "owner": "team-backend",
        "jira_ticket": "#64"
    }
}

# コード実装
def new_feature_handler():
    if not FeatureFlags.is_enabled("ENABLE_NEW_FEATURE"):
        raise FeatureNotEnabledError("New feature is disabled")
    
    # 新機能実装
    return process_new_feature()
```

### 3. 段階的ロールアウト
```python
class RolloutManager:
    """段階的ロールアウト管理"""
    
    def should_enable_for_user(self, flag_name: str, user_id: str) -> bool:
        flag_config = self.get_flag_config(flag_name)
        rollout_percentage = flag_config.get("rollout_percentage", 0)
        
        if rollout_percentage >= 100:
            return True
        
        # ユーザーIDベースの決定的な判定
        import hashlib
        hash_input = f"{flag_name}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
        return (hash_value % 100) < rollout_percentage
```

### 4. 監視・メトリクス
```python
def track_flag_usage(flag_name: str, enabled: bool, context: Dict[str, Any]):
    """フラグ使用状況の追跡"""
    logger.info("Feature flag evaluated", extra={
        "flag_name": flag_name,
        "enabled": enabled,
        "user_id": context.get("user_id"),
        "environment": context.get("environment"),
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # メトリクス送信
    metrics.increment(f"feature_flag.{flag_name}.evaluated")
    if enabled:
        metrics.increment(f"feature_flag.{flag_name}.enabled")
```

### 5. 削除フェーズ
```python
# 削除前チェックリスト
def prepare_flag_removal(flag_name: str):
    """フラグ削除前の確認"""
    
    # 1. 使用状況確認
    usage_stats = get_flag_usage_stats(flag_name, days=30)
    if usage_stats["daily_evaluations"] > 0:
        logger.warning(f"Flag {flag_name} still in use: {usage_stats}")
    
    # 2. コード依存確認
    code_references = find_code_references(flag_name)
    if code_references:
        logger.error(f"Code still references {flag_name}: {code_references}")
        return False
    
    # 3. 設定ファイル確認
    config_references = find_config_references(flag_name)
    if config_references:
        logger.warning(f"Config references found: {config_references}")
    
    return True
```

## 設定管理

### 1. 静的設定ファイル
```yaml
# config/feature_flags.yml
flags:
  ENABLE_LLM:
    description: "LLM機能の有効化制御"
    type: "operational"
    default: false
    environments:
      development: true
      staging: true
      production: false
    
  ENABLE_BATCH_UI:
    description: "新バッチUIの表示制御"
    type: "release"
    default: false
    rollout_percentage: 25
    
  DEBUG_LOGGING:
    description: "デバッグログ出力制御"
    type: "operational"
    default: false
    runtime_configurable: true
```

### 2. 動的設定更新
```python
class DynamicFlagManager:
    """動的フラグ管理"""
    
    def update_flag(self, flag_name: str, enabled: bool):
        """実行時フラグ更新"""
        if not self.is_runtime_configurable(flag_name):
            raise ValueError(f"Flag {flag_name} is not runtime configurable")
        
        self.cache[flag_name] = enabled
        self.persist_flag_state(flag_name, enabled)
        
        logger.info(f"Flag {flag_name} updated to {enabled}")
        metrics.increment(f"feature_flag.{flag_name}.updated")
```

## エラーハンドリング

### 1. Flag 未定義エラー
```python
class FeatureFlagError(Exception):
    """フラグ関連エラー"""
    pass

class UndefinedFlagError(FeatureFlagError):
    """未定義フラグエラー"""
    pass

def is_enabled(flag_name: str) -> bool:
    if flag_name not in self.flags:
        logger.error(f"Undefined flag: {flag_name}")
        if self.strict_mode:
            raise UndefinedFlagError(f"Flag {flag_name} is not defined")
        return False  # デフォルト値
    
    return self.flags[flag_name].is_enabled()
```

### 2. 設定読み込みエラー
```python
def load_flag_config(config_path: str) -> Dict[str, Any]:
    """フラグ設定読み込み"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Flag config not found: {config_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Invalid flag config: {e}")
        raise FeatureFlagError(f"Failed to load flag config: {e}")
```

## テスト戦略

### 1. Flag テスト
```python
import pytest
from src.config.feature_flags import FeatureFlags

class TestFeatureFlags:
    
    def test_flag_enabled(self, mock_flag_config):
        """フラグ有効時のテスト"""
        mock_flag_config.return_value = {"TEST_FLAG": True}
        
        assert FeatureFlags.is_enabled("TEST_FLAG") is True
    
    def test_flag_disabled(self, mock_flag_config):
        """フラグ無効時のテスト"""
        mock_flag_config.return_value = {"TEST_FLAG": False}
        
        assert FeatureFlags.is_enabled("TEST_FLAG") is False
    
    def test_undefined_flag(self):
        """未定義フラグのテスト"""
        with pytest.raises(UndefinedFlagError):
            FeatureFlags.is_enabled("UNDEFINED_FLAG")
```

### 2. 機能テスト
```python
def test_feature_with_flag_enabled():
    """フラグ有効時の機能テスト"""
    with patch.object(FeatureFlags, 'is_enabled', return_value=True):
        result = process_with_new_feature()
        assert result.uses_new_implementation is True

def test_feature_with_flag_disabled():
    """フラグ無効時の機能テスト"""
    with patch.object(FeatureFlags, 'is_enabled', return_value=False):
        result = process_with_new_feature()
        assert result.uses_legacy_implementation is True
```

## 運用ガイドライン

### 1. フラグ管理責任
- 作成者: フラグライフサイクル管理
- チームリーダー: ロールアウト承認
- 運用チーム: 本番環境制御

### 2. 定期レビュー
```bash
# 月次フラグレビュー
python scripts/flag_audit.py --older-than 90days
python scripts/unused_flags.py --check-references
```

### 3. アラート設定
- 古いフラグ（90日以上）の検出
- 未使用フラグの識別
- 設定エラーの監視

## 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-08-26 | 初期ドラフト作成 | Copilot Agent |
| 1.1.0 | 2025-08-29 | 実装ステータス追記 (feature_flags.py / feature_flags.yaml 基盤) | Copilot Agent |

---

効果的なフラグ管理により、安全で効率的な機能リリースを実現してください。

---

## 実装ステータス (Issue #64 初版)

現在提供される最小フレームワーク:

- デフォルト定義ファイル: `config/feature_flags.yaml`
- ローダ / 解決ロジック: `src/config/feature_flags.py` (`FeatureFlags` クラス)
- 優先順位: runtime_override > environment variable > file default
- 対応型: bool / int / str
- アーティファクト: `artifacts/runs/<timestamp>-flags/feature_flags_resolved.json`
- CLI (暫定): `python scripts/flags_cli.py list|get|set|clear`

未実装 (後続 Issue 推奨):

- Gradio UI Flags パネル (一覧 + 一時 override)
- 変異 (multi-variant) / % rollout / targeting ルール
- 永続 override / 監査ログ強化 / metrics (#58) 連携

### 基本使用例

```python
from src.config.feature_flags import FeatureFlags

if FeatureFlags.is_enabled("engine.cdp_use"):
    # 新しい cdp_use エンジン処理
    pass

# 任意の一時オーバーライド (プロセス内限定)
FeatureFlags.set_override("ui.experimental_panel", True, ttl_seconds=300)

value = FeatureFlags.get("enable_llm", expected_type=bool)
```

### 環境変数オーバーライド

`engine.cdp_use` → `BYKILT_FLAG_ENGINE_CDP_USE` (または簡易 `ENGINE_CDP_USE`)

### ランタイムオーバーライド CLI 例

```bash
python scripts/flags_cli.py set engine.cdp_use false
python scripts/flags_cli.py list
```

---