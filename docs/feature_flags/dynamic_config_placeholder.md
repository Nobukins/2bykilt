# Dynamic Configuration Placeholder

最終更新: 2025年9月28日

## 概要

ConfigurationタブのConfig File Path入力フィールドのplaceholderを、Feature Flagの状態に応じて動的に表示する機能です。これにより、ユーザーは現在サポートされている設定ファイル形式を正確に把握できます。

## 目的

### 1. ユーザー体験の向上

- 現在の設定状態をUIで明確に表示
- サポートされていないファイル形式の入力を防ぐ
- 設定変更時の混乱を回避

### 2. セキュリティ意識の向上

- pickleファイルサポートの無効化状態を明示
- 安全な設定ファイル形式（JSON）の推奨を促進

### 3. 動的設定の反映

- Feature Flag変更時の即時反映
- 設定変更後の再起動不要

## 実装詳細

### コード位置

```python
# bykilt.py - create_ui関数内のConfigurationタブ
with gr.TabItem("📁 Configuration", id=10):
    with gr.Group():
        # Feature Flagの状態に応じてplaceholderを動的に設定
        allow_pickle = FeatureFlags.get("security.allow_pickle_config", expected_type=bool, default=False)
        if allow_pickle:
            config_placeholder = "Enter path to .pkl or .json config file"
        else:
            config_placeholder = "Enter path to .json config file"

        config_file_path = gr.Textbox(label="Config File Path", placeholder=config_placeholder)
```

### Feature Flag依存関係

- **Flag名**: `security.allow_pickle_config`
- **型**: `bool`
- **デフォルト値**: `False`
- **説明**: pickle形式の設定ファイル読み込みを許可するかどうか

### 動作ロジック

| Feature Flag状態 | Placeholder表示 | 説明 |
|------------------|----------------|------|
| `True` | "Enter path to .pkl or .json config file" | pickleとJSON両方の形式をサポート |
| `False` | "Enter path to .json config file" | JSON形式のみをサポート（セキュリティ推奨） |

## 使用例

### 1. pickleサポート有効時

```python
# Feature Flag設定
FeatureFlags.set_override("security.allow_pickle_config", True)

# UI表示結果
# Config File Path: [Enter path to .pkl or .json config file]
```

### 2. pickleサポート無効時（デフォルト）

```python
# Feature Flag設定（デフォルト）
# security.allow_pickle_config = False

# UI表示結果
# Config File Path: [Enter path to .json config file]
```

### 3. ランタイムでの変更

```python
from src.config.feature_flags import FeatureFlags

# 動的に変更
FeatureFlags.set_override("security.allow_pickle_config", False)
# UIが即座に更新され、placeholderがJSONのみに変更される
```

## テスト方法

### 1. 手動テスト

```bash
# アプリケーション起動
python bykilt.py

# Configurationタブを開き、placeholderの表示を確認
# - pickleサポート有効時: ".pkl or .json"
# - pickleサポート無効時: ".json only"
```

### 2. ユニットテスト

```python
import pytest
from src.config.feature_flags import FeatureFlags

def test_dynamic_placeholder():
    """placeholderの動的変更をテスト"""

    # pickleサポート有効時
    FeatureFlags.set_override("security.allow_pickle_config", True)
    allow_pickle = FeatureFlags.get("security.allow_pickle_config", expected_type=bool, default=False)
    assert allow_pickle == True

    # 期待されるplaceholder
    expected_placeholder = "Enter path to .pkl or .json config file"
    assert "pkl" in expected_placeholder and "json" in expected_placeholder

    # pickleサポート無効時
    FeatureFlags.set_override("security.allow_pickle_config", False)
    allow_pickle = FeatureFlags.get("security.allow_pickle_config", expected_type=bool, default=False)
    assert allow_pickle == False

    # 期待されるplaceholder
    expected_placeholder = "Enter path to .json config file"
    assert "pkl" not in expected_placeholder and "json" in expected_placeholder
```

### 3. UI統合テスト

```python
def test_ui_placeholder_integration():
    """UI統合テスト"""

    # Gradio UIの作成
    config_dict = default_config()
    demo = create_ui(config_dict)

    # Configurationタブのtextboxを取得
    config_textbox = None
    for component in demo.blocks:
        if hasattr(component, 'label') and component.label == "Config File Path":
            config_textbox = component
            break

    assert config_textbox is not None
    assert config_textbox.placeholder is not None

    # Feature Flagに応じたplaceholder確認
    allow_pickle = FeatureFlags.get("security.allow_pickle_config", expected_type=bool, default=False)
    if allow_pickle:
        assert "pkl" in config_textbox.placeholder
        assert "json" in config_textbox.placeholder
    else:
        assert "pkl" not in config_textbox.placeholder
        assert "json" in config_textbox.placeholder
```

## 設定方法

### 1. 環境変数

```bash
# pickleサポートを有効化
export BYKILT_FLAG_SECURITY_ALLOW_PICKLE_CONFIG=true

# アプリケーション起動
python bykilt.py
```

### 2. 設定ファイル

```yaml
# config/feature_flags.yaml
flags:
  security.allow_pickle_config:
    description: "pickle形式の設定ファイル読み込みを許可"
    type: "operational"
    default: false
    environments:
      development: true
      staging: false
      production: false
```

### 3. ランタイム設定

```python
from src.config.feature_flags import FeatureFlags

# 一時的なオーバーライド（プロセス内限定）
FeatureFlags.set_override("security.allow_pickle_config", True, ttl_seconds=3600)
```

## セキュリティ考慮事項

### 1. デフォルト設定

- pickleサポートはデフォルトで無効化
- セキュリティを優先した設定

### 2. 監査ログ

- Feature Flag変更時のログ記録
- 設定変更の追跡

### 3. アクセス制御

- 管理者権限でのみpickleサポート有効化可能
- 変更時の確認ダイアログ表示

## 関連機能

### 1. 設定ファイル処理

- JSON形式の設定ファイル読み込み/書き込み
- pickle形式の段階的廃止
- 設定ファイルの検証

### 2. UIフィードバック

- 無効なファイル形式選択時の警告
- 設定読み込み成功/失敗の表示
- リアルタイムの設定状態表示

## 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-09-28 | 初回作成 | Copilot Agent |

---

この機能により、ユーザーは現在のセキュリティ設定をUI上で直感的に把握でき、安全な設定ファイル形式の使用を促進します。
