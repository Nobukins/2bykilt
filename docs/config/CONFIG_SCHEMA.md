# Configuration Schema & Versioning

最終更新: 2025-08-26

## 概要

2bykilt プロジェクトの設定管理スキーマとバージョニング戦略を定義します。多環境対応と後方互換性を重視した設計です。

## スキーマ設計原則

### 1. 後方互換性
- 設定項目の削除は非推奨警告後に実施
- デフォルト値による新項目の安全な追加
- スキーマバージョンによる段階的移行

### 2. 環境別設定
- 開発・ステージング・本番環境対応
- 環境変数による設定オーバーライド
- セキュリティレベル別の設定分離

### 3. バリデーション
- スキーマ定義による厳密な検証
- 実行時バリデーションとエラーハンドリング
- 設定値の整合性チェック

## スキーマ構造

### 1. 基本スキーマ定義
```yaml
# config/schema/v1.0.yml
schema_version: "1.0"
config_version: "1.0.0"

sections:
  application:
    required: true
    description: "アプリケーション基本設定"
    
  logging:
    required: true
    description: "ログ出力設定"
    
  feature_flags:
    required: false
    description: "フィーチャーフラグ設定"
    
  security:
    required: true
    description: "セキュリティ設定"
    
  performance:
    required: false
    description: "パフォーマンス関連設定"
```

### 2. 詳細設定項目
```yaml
# Application Section
application:
  name:
    type: string
    default: "2bykilt"
    description: "アプリケーション名"
    
  version:
    type: string
    required: true
    description: "アプリケーションバージョン"
    
  environment:
    type: enum
    values: ["development", "staging", "production"]
    default: "development"
    description: "実行環境"
    
  debug_mode:
    type: boolean
    default: false
    environment_override: "DEBUG"
    description: "デバッグモード有効化"

# Logging Section  
logging:
  level:
    type: enum
    values: ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    default: "INFO"
    environment_override: "LOG_LEVEL"
    
  format:
    type: enum
    values: ["json", "plain", "structured"]
    default: "json"
    description: "ログ出力形式"
    
  output:
    console:
      enabled:
        type: boolean
        default: true
      format:
        type: string
        default: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
    file:
      enabled:
        type: boolean
        default: false
        environment_override: "LOG_TO_FILE"
      path:
        type: string
        default: "logs/app.log"
        environment_override: "LOG_FILE_PATH"
      rotation:
        max_size:
          type: string
          default: "10MB"
        backup_count:
          type: integer
          default: 5

# Feature Flags Section
feature_flags:
  provider:
    type: enum
    values: ["static", "dynamic", "external"]
    default: "static"
    
  config_file:
    type: string
    default: "config/feature_flags.yml"
    description: "フラグ設定ファイル"
    
  runtime_updates:
    type: boolean
    default: false
    description: "実行時更新許可"

# Security Section
security:
  secret_key:
    type: string
    required: true
    environment_override: "SECRET_KEY"
    sensitive: true
    description: "アプリケーション暗号化キー"
    
  api_keys:
    openai:
      type: string
      required: false
      environment_override: "OPENAI_API_KEY"
      sensitive: true
      
    google:
      type: string
      required: false
      environment_override: "GOOGLE_API_KEY"
      sensitive: true
      
  sandbox:
    enabled:
      type: boolean
      default: true
      description: "サンドボックス実行"
      
    allowed_paths:
      type: array
      items:
        type: string
      default: ["/tmp", "/var/tmp"]
      description: "許可されたパス"

# Performance Section
performance:
  max_workers:
    type: integer
    default: 4
    minimum: 1
    maximum: 32
    environment_override: "MAX_WORKERS"
    
  timeout:
    request:
      type: integer
      default: 30
      description: "リクエストタイムアウト（秒）"
      
    llm_response:
      type: integer
      default: 120
      description: "LLMレスポンスタイムアウト（秒）"
      
  cache:
    enabled:
      type: boolean
      default: true
      
    ttl:
      type: integer
      default: 3600
      description: "キャッシュTTL（秒）"
```

## バージョニング戦略

### 1. セマンティックバージョニング
```yaml
# バージョン形式: MAJOR.MINOR.PATCH
# MAJOR: 非互換な変更
# MINOR: 後方互換性のある機能追加
# PATCH: 後方互換性のあるバグ修正

version_history:
  "1.0.0": "初期リリース"
  "1.1.0": "Feature flags 設定追加"
  "1.1.1": "デフォルト値修正"
  "2.0.0": "セキュリティ設定の再構成"
```

### 2. マイグレーション定義
```python
# config/migrations/v1_to_v2.py
class ConfigMigrationV1ToV2:
    """設定スキーマ v1.x から v2.0 への移行"""
    
    def migrate(self, old_config: Dict[str, Any]) -> Dict[str, Any]:
        new_config = old_config.copy()
        
        # 1. 廃止項目の警告
        if 'deprecated_setting' in old_config:
            logger.warning("deprecated_setting is no longer supported")
            del new_config['deprecated_setting']
        
        # 2. 新項目のデフォルト値設定
        if 'security' not in new_config:
            new_config['security'] = {
                'sandbox': {'enabled': True}
            }
        
        # 3. 構造変更
        if 'old_logging_config' in old_config:
            new_config['logging'] = self._migrate_logging_config(
                old_config['old_logging_config']
            )
            del new_config['old_logging_config']
        
        new_config['config_version'] = "2.0.0"
        return new_config
```

### 3. 互換性チェック
```python
def check_compatibility(config: Dict[str, Any]) -> List[str]:
    """設定互換性チェック"""
    warnings = []
    config_version = config.get('config_version', '1.0.0')
    
    if version.parse(config_version) < version.parse('1.1.0'):
        warnings.append("Feature flags section missing - using defaults")
    
    if version.parse(config_version) < version.parse('2.0.0'):
        warnings.append("Security configuration outdated - migration recommended")
    
    return warnings
```

## 環境別設定管理

### 1. 設定ファイル階層
```
config/
├── schema/
│   ├── v1.0.yml          # スキーマ定義
│   └── v2.0.yml
├── base.yml              # 基本設定
├── development.yml       # 開発環境
├── staging.yml           # ステージング環境
└── production.yml        # 本番環境
```

### 2. 設定ローダー実装
```python
from typing import Dict, Any, Optional
import yaml
import os
from pathlib import Path

class ConfigLoader:
    """設定ローダー"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        
    def load_config(self, environment: str = None) -> Dict[str, Any]:
        """環境別設定読み込み"""
        if not environment:
            environment = os.getenv('ENVIRONMENT', 'development')
        
        # 1. ベース設定読み込み
        base_config = self._load_yaml_file('base.yml')
        
        # 2. 環境別設定読み込み
        env_config = self._load_yaml_file(f'{environment}.yml')
        
        # 3. 設定マージ
        config = self._merge_configs(base_config, env_config)
        
        # 4. 環境変数オーバーライド
        config = self._apply_env_overrides(config)
        
        # 5. バリデーション
        self._validate_config(config)
        
        return config
    
    def _load_yaml_file(self, filename: str) -> Dict[str, Any]:
        """YAML ファイル読み込み"""
        file_path = self.config_dir / filename
        if not file_path.exists():
            return {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """設定マージ（深い結合）"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """環境変数オーバーライド適用"""
        schema = self._load_schema(config.get('config_version', '1.0.0'))
        
        def apply_overrides(cfg: Dict[str, Any], schema_section: Dict[str, Any]):
            for key, value in cfg.items():
                if isinstance(value, dict):
                    apply_overrides(value, schema_section.get(key, {}))
                else:
                    env_var = schema_section.get('environment_override')
                    if env_var and env_var in os.environ:
                        cfg[key] = self._convert_env_value(os.environ[env_var], schema_section.get('type', 'string'))
        
        apply_overrides(config, schema)
        return config
```

## バリデーション実装

### 1. スキーマバリデータ
```python
from jsonschema import validate, ValidationError
import jsonschema

class ConfigValidator:
    """設定バリデータ"""
    
    def __init__(self, schema_dir: str = "config/schema"):
        self.schema_dir = Path(schema_dir)
        
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """設定バリデーション"""
        errors = []
        
        try:
            # 1. スキーマ バリデーション
            schema = self._load_schema(config.get('config_version', '1.0.0'))
            validate(instance=config, schema=schema)
            
            # 2. ビジネス ルール チェック
            errors.extend(self._validate_business_rules(config))
            
            # 3. 整合性チェック
            errors.extend(self._validate_consistency(config))
            
        except ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return errors
    
    def _validate_business_rules(self, config: Dict[str, Any]) -> List[str]:
        """ビジネスルール検証"""
        errors = []
        
        # ルール1: 本番環境ではデバッグモード無効
        if (config.get('application', {}).get('environment') == 'production' and 
            config.get('application', {}).get('debug_mode', False)):
            errors.append("Debug mode must be disabled in production")
        
        # ルール2: LLM有効時はAPIキー必須
        if (config.get('feature_flags', {}).get('enable_llm', False) and
            not config.get('security', {}).get('api_keys', {}).get('openai')):
            errors.append("OpenAI API key required when LLM is enabled")
        
        return errors
    
    def _validate_consistency(self, config: Dict[str, Any]) -> List[str]:
        """整合性検証"""
        errors = []
        
        # 整合性1: ログファイル出力時はパス必須
        logging_config = config.get('logging', {})
        if (logging_config.get('output', {}).get('file', {}).get('enabled', False) and
            not logging_config.get('output', {}).get('file', {}).get('path')):
            errors.append("Log file path required when file logging is enabled")
        
        return errors
```

## 設定の動的更新

### 1. 実行時設定変更
```python
class DynamicConfigManager:
    """動的設定管理"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.watchers = []
        
    def update_setting(self, path: str, value: Any):
        """設定値更新"""
        keys = path.split('.')
        current = self.config
        
        # 更新対象までナビゲート
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 値更新
        old_value = current.get(keys[-1])
        current[keys[-1]] = value
        
        # 変更通知
        self._notify_watchers(path, old_value, value)
        
        logger.info(f"Configuration updated: {path} = {value}")
    
    def watch_setting(self, path: str, callback: Callable):
        """設定変更監視"""
        self.watchers.append({
            'path': path,
            'callback': callback
        })
    
    def _notify_watchers(self, path: str, old_value: Any, new_value: Any):
        """変更通知"""
        for watcher in self.watchers:
            if watcher['path'] == path:
                try:
                    watcher['callback'](path, old_value, new_value)
                except Exception as e:
                    logger.error(f"Watcher callback failed: {e}")
```

## セキュリティ考慮事項

### 1. 機密情報管理
```python
class SecureConfigHandler:
    """セキュア設定処理"""
    
    SENSITIVE_KEYS = [
        'secret_key', 'api_key', 'password', 'token', 'private_key'
    ]
    
    def sanitize_config_for_logging(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """ログ用設定サニタイズ"""
        sanitized = {}
        
        for key, value in config.items():
            if isinstance(value, dict):
                sanitized[key] = self.sanitize_config_for_logging(value)
            elif any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def encrypt_sensitive_values(self, config: Dict[str, Any], key: bytes) -> Dict[str, Any]:
        """機密値暗号化"""
        from cryptography.fernet import Fernet
        f = Fernet(key)
        
        def encrypt_recursive(cfg):
            for k, v in cfg.items():
                if isinstance(v, dict):
                    encrypt_recursive(v)
                elif any(sensitive in k.lower() for sensitive in self.SENSITIVE_KEYS):
                    if isinstance(v, str):
                        cfg[k] = f.encrypt(v.encode()).decode()
        
        encrypted_config = config.copy()
        encrypt_recursive(encrypted_config)
        return encrypted_config
```

## 運用ガイドライン

### 1. 設定変更プロセス
1. 設定変更提案（Issue作成）
2. スキーマ更新（必要に応じて）
3. 設定ファイル更新
4. バリデーション確認
5. 段階的デプロイ（dev → staging → prod）

### 2. 監視・アラート
```python
def monitor_config_health():
    """設定健全性監視"""
    
    # 1. 設定ファイル整合性チェック
    for env in ['development', 'staging', 'production']:
        try:
            config = ConfigLoader().load_config(env)
            errors = ConfigValidator().validate_config(config)
            if errors:
                alert(f"Config validation failed for {env}: {errors}")
        except Exception as e:
            alert(f"Config loading failed for {env}: {e}")
    
    # 2. 環境変数チェック
    required_env_vars = ['SECRET_KEY', 'DATABASE_URL']
    missing_vars = [var for var in required_env_vars if var not in os.environ]
    if missing_vars:
        alert(f"Missing required environment variables: {missing_vars}")
```

## 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-08-26 | 初期ドラフト作成 | Copilot Agent |

---

設定スキーマの適切な管理により、安定した多環境運用を実現してください。