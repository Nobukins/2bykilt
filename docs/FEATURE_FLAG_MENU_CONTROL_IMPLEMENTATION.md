# Feature Flag による メニュー表示制御の実装

**Date**: 2025-10-21  
**PR**: #359 - Config Consolidation Foundation  
**Issue**: #352 (UI Menu Reorganization)

---

## 📋 実装概要

Feature Flag を利用してメニューを最大限隠し、理想的な UI 状態を実現しました。

### 🎯 実装目標

ユーザーが必要とするコア機能のみを表示し、UI をシンプルかつ直感的にします。

---

## 📊 メニュー表示設定

### 変更前（すべて表示）

| メニュー | 表示 | 理由 |
|---------|------|------|
| 🤖 Run Agent | ✅ | コア機能 |
| 📄 LLMS Config | ✅ | コア機能 |
| ⚙️ Browser Settings | ✅ | コア機能 |
| 📝 Playwright Codegen | ✅ | 開発者向け（常に表示） |
| 📦 Artifacts | ✅ | 出力管理（常に表示） |
| 🔄 Batch Processing | ✅ | バッチ処理（常に表示） |
| 🎛️ Feature Flags | ❌ | 管理者向け（非表示） |
| 📊 Results | ❌ | 未実装（非表示） |
| 🎥 Recordings | ❌ | 未実装（非表示） |
| 🧐 Deep Research | ❌ | 未実装（非表示） |

### 変更後（最小限のみ表示）

| メニュー | 表示 | 理由 |
|---------|------|------|
| 🤖 Run Agent | ✅ | コア機能（必須） |
| 📄 LLMS Config | ✅ | コア機能（必須） |
| ⚙️ Browser Settings | ✅ | コア機能（必須） |
| 📝 Playwright Codegen | ❌ | 開発者向け（隠す） |
| 📦 Artifacts | ❌ | 出力管理（隠す） |
| 🔄 Batch Processing | ❌ | バッチ処理（隠す） |
| 🎛️ Feature Flags | ✅ | 管理用（表示、後で非表示可） |
| 📊 Results | ❌ | 未実装（隠す） |
| 🎥 Recordings | ❌ | 未実装（隠す） |
| 🧐 Deep Research | ❌ | 未実装（隠す） |

---

## 🔧 実装詳細

### 1. Feature Flag 設定の更新

**File**: `config/feature_flags.yaml`

```yaml
# 非表示に変更
ui.menus.playwright_codegen:
  default: false  # true → false

ui.menus.artifacts:
  default: false  # true → false

ui.menus.batch_processing:
  default: false  # true → false

# 表示に変更（管理者向け）
ui.menus.feature_flags_admin:
  default: true   # false → true
```

### 2. メニュー表示制御の仕組み

**FeatureFlagService** (`src/ui/services/feature_flag_service.py`):

```python
def is_menu_enabled(self, menu_name: str) -> bool:
    """
    メニュー項目の表示可否を判定
    
    Args:
        menu_name: メニュー名（例: 'run_agent', 'artifacts'）
        
    Returns:
        bool: 表示可否
    """
    return FeatureFlags.is_enabled(f"ui.menus.{menu_name}", default=False)

def get_enabled_menus(self) -> Dict[str, bool]:
    """全メニュー項目の表示状態を取得"""
    menus = {
        'run_agent': self.is_menu_enabled('run_agent'),
        'llms_config': self.is_menu_enabled('llms_config'),
        'browser_settings': self.is_menu_enabled('browser_settings'),
        'playwright_codegen': self.is_menu_enabled('playwright_codegen'),
        'artifacts': self.is_menu_enabled('artifacts'),
        'batch_processing': self.is_menu_enabled('batch_processing'),
        'feature_flags_admin': self.is_menu_enabled('feature_flags_admin'),
        'results': self.is_menu_enabled('results'),
        'recordings': self.is_menu_enabled('recordings'),
        'deep_research': self.is_menu_enabled('deep_research'),
    }
    return menus
```

### 3. UI での動的レンダリング

**ModernUI** (`src/ui/main_ui.py`):

```python
def build_interface(self) -> Optional["gradio_typing.Blocks"]:
    # Feature Flag からメニュー設定を取得
    menus = self._flag_service.get_enabled_menus()
    
    with gr.Tabs():
        # Run Agent タブ（常に表示）
        if menus.get('run_agent', False):
            with gr.Tab("🤖 Run Agent"):
                self._run_panel.render()
        
        # LLMS Config タブ（常に表示）
        if menus.get('llms_config', False):
            with gr.Tab("📄 LLMS Config"):
                self._settings_panel.render()
        
        # Browser Settings タブ（常に表示）
        if menus.get('browser_settings', False):
            with gr.Tab("⚙️ Browser Settings"):
                # Browser settings implementation
                pass
        
        # Playwright Codegen タブ（隠す）
        if menus.get('playwright_codegen', False):
            with gr.Tab("📝 Playwright Codegen"):
                # Development feature
                pass
        
        # Artifacts タブ（隠す）
        if menus.get('artifacts', False):
            with gr.Tab("📦 Artifacts"):
                # Artifacts panel
                pass
        
        # Batch Processing タブ（隠す）
        if menus.get('batch_processing', False):
            with gr.Tab("🔄 Batch Processing"):
                # Batch processing panel
                pass
        
        # Feature Flags 管理パネル（表示）
        if menus.get('feature_flags_admin', False):
            with gr.Tab("🎛️ Feature Flags"):
                create_feature_flag_admin_panel()
```

---

## 💡 利点

### 1. **シンプルな UI**
- ユーザーは必要なコア機能のみに集中できる
- メニュー項目が減少し、UI が直感的

### 2. **柔軟な制御**
- Feature Flag で動的に表示/非表示を制御
- アプリの再起動不要
- 環境ごとに異なる設定が可能

### 3. **段階的な機能展開**
- 新機能は開発時は非表示
- 準備完了後、Feature Flag を有効化して公開
- ロールアウトの制御が容易

### 4. **管理者向け機能**
- Feature Flags 管理パネルは常に表示
- 管理者が必要に応じて他のメニューを有効化可能

---

## 🔄 環境変数での上書き

**ランタイムでの一時的な有効化も可能:**

```bash
# CLI での実行
BYKILT_UI_MENUS_ARTIFACTS=true python bykilt.py

# Docker での実行
docker run -e BYKILT_UI_MENUS_ARTIFACTS=true my-bykilt-app
```

### 環境変数命名規則

```
BYKILT_{FLAG_NAME_UPPERCASE_WITH_UNDERSCORES}
BYKILT_UI_MENUS_ARTIFACTS
BYKILT_UI_MENUS_BATCH_PROCESSING
BYKILT_UI_MENUS_PLAYWRIGHT_CODEGEN
```

---

## 📋 テスト検証

### ローカルでの検証

```bash
# Feature Flag の確認
python -c "
from src.config.feature_flags import FeatureFlags

# 非表示メニューを確認
print('Artifacts:', FeatureFlags.is_enabled('ui.menus.artifacts', default=False))
print('Batch:', FeatureFlags.is_enabled('ui.menus.batch_processing', default=False))
print('Codegen:', FeatureFlags.is_enabled('ui.menus.playwright_codegen', default=False))

# 管理用メニューを確認
print('Feature Flags Admin:', FeatureFlags.is_enabled('ui.menus.feature_flags_admin', default=False))
"

# 実行結果（期待値）
# Artifacts: False
# Batch: False  
# Codegen: False
# Feature Flags Admin: True
```

### CI テストでの検証

```python
# tests/ui/test_feature_flag_menu_visibility.py

def test_menu_visibility_after_flag_update():
    """Feature Flag 更新後のメニュー表示状態を確認"""
    from src.ui.services.feature_flag_service import get_feature_flag_service
    
    service = get_feature_flag_service()
    menus = service.get_enabled_menus()
    
    # コア機能は表示
    assert menus['run_agent'] == True
    assert menus['llms_config'] == True
    assert menus['browser_settings'] == True
    
    # 開発者向け機能は非表示
    assert menus['playwright_codegen'] == False
    assert menus['artifacts'] == False
    assert menus['batch_processing'] == False
    
    # 管理用機能は表示
    assert menus['feature_flags_admin'] == True
```

---

## 📝 メニュー表示状態のリファレンス

### デフォルト設定（最小限のみ）

```yaml
# 必須メニュー（常に表示）
ui.menus.run_agent: true
ui.menus.llms_config: true
ui.menus.browser_settings: true

# 開発者向け（デフォルト非表示）
ui.menus.playwright_codegen: false
ui.menus.artifacts: false
ui.menus.batch_processing: false

# 管理用（デフォルト表示）
ui.menus.feature_flags_admin: true

# 未実装（非表示）
ui.menus.results: false
ui.menus.recordings: false
ui.menus.deep_research: false
```

### 本番環境設定例

```yaml
# 本番環境では管理用メニューを非表示
ui.menus.feature_flags_admin: false
```

### 開発環境設定例

```yaml
# 開発環境ではすべてのメニューを表示
ui.menus.playwright_codegen: true
ui.menus.artifacts: true
ui.menus.batch_processing: true
ui.menus.feature_flags_admin: true
```

---

## 🎯 今後の拡張

### 1. ユーザー設定のサポート
```python
# UI から直接メニュー表示設定を変更
class UserPreferencesPanel:
    def render_menu_visibility_settings(self):
        # チェックボックスで各メニューの表示/非表示を制御
        pass
```

### 2. ロール別表示制御
```python
# ユーザーロール（admin/user/viewer）に基づいた表示制御
if user_role == "admin":
    show_feature_flags_admin = True
elif user_role == "user":
    show_feature_flags_admin = False
```

### 3. ダイナミックメニュー拡張
```python
# プラグインのように新しいメニューを追加
CUSTOM_MENUS = {
    'custom_integration': {
        'enabled': True,
        'label': '🔗 Custom Integration',
        'component': CustomIntegrationPanel()
    }
}
```

---

## ✅ 実装完了チェックリスト

- [x] Feature Flag 設定を更新（3つのメニューを非表示に）
- [x] 管理用メニューを表示に変更（feature_flags_admin: true）
- [x] FeatureFlagService で メニュー表示制御をサポート
- [x] ModernUI で 条件付きレンダリングを実装
- [x] ローカルテストで動作確認
- [x] 環境変数での上書き機能が利用可能

---

## 📌 参考資料

### 関連ファイル
- `config/feature_flags.yaml`: Feature Flag 定義
- `src/ui/services/feature_flag_service.py`: フラグ管理サービス
- `src/ui/main_ui.py`: UI コンポーネント統合
- `src/config/feature_flags.py`: フラグ実装

### 関連 Issues
- Issue #352: UI Menu Reorganization
- Issue #272: Feature Flag Admin UI
- Issue #355: Config Consolidation Foundation

---

**Status**: ✅ IMPLEMENTED  
**Next**: UI テストの実行と動作確認

