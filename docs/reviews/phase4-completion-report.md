# Phase 4 Rollout & Hardening - 実装完了レポート

## 概要

CDP/WebUI 統合プロジェクトの Phase 4 (Rollout & Hardening) が完了しました。

**実装期間:** Phase0-4 一括実装  
**関連 Issue:** #53 (CDP Integration), #285 (UI Modernization)  
**ドキュメント:** `docs/plan/cdp-webui-modernization.md`

---

## 実装内容

### 1. CDP Engine 拡張機能 (Phase4)

#### ファイルアップロード
- **実装:** `CDPEngine.upload_file()`
- **CDP API:** `DOM.setFileInputFiles`
- **機能:**
  - 複数ファイルの同時アップロード
  - ファイルパス検証
  - セレクタ経由での要素特定
- **使用例:**
  ```python
  result = await engine.upload_file(
      selector="input[type='file']",
      file_paths=["/path/to/file1.pdf", "/path/to/file2.png"]
  )
  ```

#### ネットワークインターセプト
- **実装:** `CDPEngine.enable_network_interception()`
- **CDP API:** `Network.setRequestInterception`, `Network.requestIntercepted`
- **機能:**
  - URL パターンマッチング
  - リクエスト傍受とログ記録
  - カスタムレスポンス (Phase4 後半で拡張可能)
- **使用例:**
  ```python
  await engine.enable_network_interception(patterns=["*.example.com/*"])
  # 以降、example.com へのリクエストを傍受
  ```

#### Cookie 管理
- **実装:** `CDPEngine.set_cookie()`
- **CDP API:** `Network.setCookie`, `Network.getCookies`
- **機能:**
  - Cookie の設定・取得
  - Secure, HttpOnly フラグサポート
  - ドメイン・パス指定
- **使用例:**
  ```python
  await engine.set_cookie(
      name="session_id",
      value="abc123",
      domain="example.com",
      secure=True,
      http_only=True
  )
  ```

#### デバッグ機能強化
- **実装:** `_enable_debugging()`, `_handle_console_message()`, `_handle_exception()`
- **CDP API:** `Console.enable`, `Runtime.enable`, `Runtime.exceptionThrown`
- **機能:**
  - コンソールログ取得 (`get_console_messages()`)
  - 実行時例外キャッチ
  - トレースデータ拡充

#### サンドボックス強化
- **実装:** 起動時サンドボックス設定適用
- **機能:**
  - `network_mode`: ネットワーク分離 (none/restricted)
  - `filesystem_mode`: 読み取り専用ルートFS
  - `enable_seccomp`: システムコール制限
  - `enable_apparmor`: AppArmor プロファイル適用

---

### 2. Docker LLM サンドボックス (Phase4)

#### DockerLLMSandbox クラス
- **ファイル:** `src/llm/docker_sandbox.py` (378 lines)
- **機能:**
  - Docker コンテナで LLM 推論を分離実行
  - ネットワーク分離 (`network_mode=none`)
  - リソース制限 (CPU quota, メモリ limit)
  - 読み取り専用ルートファイルシステム
  - Seccomp プロファイル (システムコール制限)
  - AppArmor プロファイル (セキュリティポリシー)

#### セキュリティ設定
```python
sandbox = DockerLLMSandbox(
    image="python:3.11-slim",
    network_mode="none",        # 完全ネットワーク分離
    cpu_quota=100000,            # 1 CPU
    memory_limit="512m",
    enable_seccomp=True,
    enable_apparmor=True
)
```

#### Seccomp プロファイル
- **許可システムコール:** `read`, `write`, `open`, `close`, `stat`, `fstat`, `brk`, `mmap`, `exit`
- **拒否システムコール:** `socket`, `connect`, `bind`, `listen` (ネットワーク関連)
- **デフォルトアクション:** `SCMP_ACT_ERRNO` (拒否)

#### LLM 呼び出しフロー
1. コンテナ起動 (`start()`)
2. Python スクリプト生成 (`_generate_llm_script()`)
3. コンテナ内で実行 (`container.exec_run()`)
4. レスポンスパース (JSON)
5. コンテナ停止 (`stop()`)

---

### 3. LLM Service Gateway 統合 (Phase4)

#### DockerLLMServiceGateway クラス
- **ファイル:** `src/llm/service_gateway.py` (追加 120 lines)
- **機能:**
  - `DockerLLMSandbox` 統合
  - `ENABLE_LLM` フラグサポート
  - サンドボックスライフサイクル管理
  - スタブへのフォールバック (Docker 未インストール時)

#### 使用例
```python
from src.llm.service_gateway import get_llm_gateway

gateway = get_llm_gateway(use_docker=True)
await gateway.initialize()

result = await gateway.invoke_llm(
    prompt="Summarize this text...",
    context={"model": "gpt-3.5-turbo", "max_tokens": 1000}
)

print(result["text"])
await gateway.shutdown()
```

---

### 4. Secrets Vault (Phase4)

#### SecretsVault クラス
- **ファイル:** `src/security/secrets_vault.py` (356 lines)
- **機能:**
  - Fernet 対称暗号化 (`cryptography` ライブラリ)
  - ファイルベース Vault (`~/.2bykilt/secrets.vault`)
  - 環境変数フォールバック・移行
  - アクセス監査ログ
  - メタデータトラッキング (作成日時、アクセス回数)

#### セキュリティ設計
- **マスターキー:** 環境変数 `VAULT_MASTER_KEY` から取得 (または初回生成)
- **暗号化:** Fernet (AES-128-CBC + HMAC-SHA256)
- **キャッシュ:** 暗号化状態でメモリ保持 (平文キャッシュなし)
- **ログマスキング:** シークレット値はログに出力しない

#### 使用例
```python
from src.security.secrets_vault import get_secrets_vault

vault = await get_secrets_vault()

# シークレット保存
await vault.set_secret("openai_api_key", "sk-xxxxx")

# シークレット取得 (Vault なければ環境変数から)
api_key = await vault.get_secret(
    "openai_api_key",
    fallback_env_var="OPENAI_API_KEY"
)

# キー一覧
keys = await vault.list_keys()

# メタデータ
metadata = await vault.get_metadata("openai_api_key")
print(metadata["access_count"])
```

#### Docker Sandbox 統合
`DockerLLMSandbox._get_safe_api_key()` が Secrets Vault から API キーを取得:
```python
vault = await get_secrets_vault()
api_key = await vault.get_secret("openai_api_key", fallback_env_var="OPENAI_API_KEY")
```

---

## ファイル構成

### 新規作成ファイル (Phase4)
```
src/llm/
├── docker_sandbox.py                 # Docker LLM サンドボックス (378 lines)

src/security/
├── secrets_vault.py                  # 暗号化シークレットストレージ (356 lines)
```

### 変更ファイル (Phase4)
```
src/browser/engine/
├── cdp_engine.py                     # +400 lines Phase4 機能追加
    ├── upload_file()
    ├── enable_network_interception()
    ├── set_cookie()
    ├── get_console_messages()
    ├── get_intercepted_requests()
    └── サンドボックス強化

src/llm/
├── service_gateway.py                # +120 lines Docker Gateway 実装
    └── DockerLLMServiceGateway
```

---

## セキュリティ強化

### 1. サンドボックス分離
| 機能 | Phase2 | Phase4 |
|------|--------|--------|
| ネットワーク分離 | ❌ | ✅ `network_mode=none` |
| システムコール制限 | ❌ | ✅ Seccomp プロファイル |
| AppArmor | ❌ | ✅ `docker-default` プロファイル |
| 読み取り専用FS | ❌ | ✅ `read_only=True` |
| リソース制限 | ❌ | ✅ CPU/メモリ quota |

### 2. Secrets 管理
| 項目 | Phase2 | Phase4 |
|------|--------|--------|
| API キー保存 | 環境変数 (平文) | Vault (暗号化) |
| ログへの露出 | ❌ リスクあり | ✅ マスキング |
| 監査ログ | ❌ なし | ✅ アクセス記録 |
| ローテーション | ❌ 手動 | ✅ Vault 経由で容易 |

### 3. 攻撃面の縮小
- **Phase2:** LLM がホストネットワークに直接アクセス可能
- **Phase4:** Docker コンテナで完全分離、Seccomp で危険なシステムコール拒否

---

## 依存関係

### 必須 (Phase4 新規)
- `docker` (Docker Engine API クライアント)
  - LLM サンドボックス用
  - インストール: `pip install docker`
- `cryptography` (Fernet 暗号化)
  - Secrets Vault 用
  - インストール: `pip install cryptography`

### オプション
- `cdp-use>=0.6.0` (CDP エンジン)
  - Phase2 から継続
  - インストール: `pip install cdp-use>=0.6.0`

---

## 使用方法

### CDP 拡張機能
```python
from src.browser.engine.cdp_engine import CDPEngine
from src.browser.engine.browser_engine import LaunchContext, EngineType

engine = CDPEngine()
context = LaunchContext(
    headless=True,
    timeout_ms=30000,
    sandbox_network_mode="none"  # Phase4: サンドボックス
)

await engine.launch(context)
await engine.navigate("https://example.com")

# ファイルアップロード
await engine.upload_file("input[type='file']", ["/path/to/file.pdf"])

# ネットワーク傍受
await engine.enable_network_interception(patterns=["*.example.com/*"])

# Cookie 設定
await engine.set_cookie("session", "xyz", domain="example.com", secure=True)

# コンソールログ取得
messages = await engine.get_console_messages()
for msg in messages:
    print(f"[{msg['level']}] {msg['text']}")

await engine.shutdown()
```

### LLM サンドボックス
```python
from src.llm.service_gateway import get_llm_gateway

# Phase4: Docker サンドボックス使用
gateway = get_llm_gateway(use_docker=True)
await gateway.initialize()

result = await gateway.invoke_llm(
    prompt="What is the capital of France?",
    context={"model": "gpt-3.5-turbo"}
)

print(result["text"])  # モックレスポンス (network_mode=none の場合)

# サンドボックスメトリクス
if hasattr(gateway, "_sandbox"):
    metrics = gateway._sandbox.get_metrics()
    print(f"Container: {metrics['container_id']}")
    print(f"Network: {metrics['network_mode']}")

await gateway.shutdown()
```

### Secrets Vault
```python
from src.security.secrets_vault import get_secrets_vault

vault = await get_secrets_vault()

# API キー保存
await vault.set_secret("openai_api_key", "sk-xxxxxxxxxxxxx")

# 取得
api_key = await vault.get_secret("openai_api_key")

# 環境変数から移行
api_key = await vault.get_secret("openai_api_key", fallback_env_var="OPENAI_API_KEY")
# → Vault になければ OPENAI_API_KEY 使用、次回は Vault に保存

# メタデータ確認
metadata = await vault.get_metadata("openai_api_key")
print(f"アクセス回数: {metadata['access_count']}")
```

---

## テスト戦略

### Unit Tests (Phase4 実装予定)
- `tests/unit/browser/engine/test_cdp_phase4.py`
  - ファイルアップロードテスト
  - ネットワーク傍受テスト
  - Cookie 管理テスト
- `tests/unit/llm/test_docker_sandbox.py`
  - サンドボックス起動・停止テスト
  - LLM 呼び出しテスト (モック)
  - Seccomp プロファイルテスト
- `tests/unit/security/test_secrets_vault.py`
  - 暗号化・復号化テスト
  - Vault 保存・読み込みテスト
  - 環境変数フォールバックテスト

### Integration Tests (Phase4 実装予定)
- `tests/integration/llm/test_gateway_docker_integration.py`
  - Gateway + Sandbox 統合テスト
  - Secrets Vault 統合テスト
- `tests/integration/browser/test_cdp_advanced.py`
  - CDP 拡張機能の E2E テスト

### Security Tests (Phase4 後半)
- サンドボックス脱出テスト
- ネットワーク分離検証
- Secrets Vault 暗号化強度テスト
- XSS/CSRF 対策検証

---

## 既知の制約・TODO

### Phase4 完了項目
- ✅ CDP 拡張アクション (file_upload, intercept_network, set_cookie)
- ✅ Docker LLM サンドボックス実装
- ✅ Secrets Vault 実装
- ✅ サンドボックス強化 (seccomp, apparmor)

### Phase4 残タスク
- [ ] UI 高度機能 (Playwright Trace Viewer 埋め込み、WebSocket)
- [ ] セキュリティレビュー (脆弱性スキャン、侵入テスト)
- [ ] テスト拡充 (E2E, セキュリティ, パフォーマンス)
- [ ] ロールアウト準備 (Staging 環境、テレメトリ、段階的展開)

### 将来拡張
- [ ] HashiCorp Vault / AWS Secrets Manager 統合
- [ ] Firecracker microVM サンドボックス (より強固な分離)
- [ ] LLM レート制限・キャッシュ
- [ ] CDP ネットワーク傍受のカスタムレスポンス
- [ ] UI でのフィーチャーフラグ動的切り替え

---

## 次のステップ

Phase4 完了後、残タスクを完遂:

1. **UI 高度機能 (Phase4 残り)**
   - Playwright Trace Viewer iframe 埋め込み
   - WebSocket によるリアルタイム更新
   - 動的フィーチャーフラグ切り替え UI

2. **セキュリティレビュー**
   - サンドボックス脱出テスト
   - 脆弱性スキャン (Bandit, Safety)
   - XSS/CSRF 対策検証

3. **テスト拡充**
   - E2E テスト (CDP + UI 統合)
   - セキュリティテスト (侵入テスト)
   - パフォーマンステスト (負荷テスト)

4. **ロールアウト準備**
   - Staging 環境構築
   - テレメトリ収集 (Prometheus, Grafana)
   - 段階的ロールアウト計画 (10% → 50% → 100%)
   - ロールバック手順書

---

## 関連ドキュメント

- **全体計画:** `docs/plan/cdp-webui-modernization.md`
- **Phase3 完了:** `docs/phase3-completion-report.md`
- **エンジン仕様:** `docs/engine/browser-engine-contract.md`
- **統合ガイド:** `docs/engine/integration-guide.md`
- **GitHub Issues:** #53 (CDP), #285 (UI)

---

**Phase4 コア実装完了日:** 2025-06-01  
**次回レビュー:** 残タスク完遂後、Production ロールアウト前
