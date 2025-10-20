# サンドボックス実行仕様 (Issue #62)

## 概要

**バージョン**: 1.0 (PoC Phase - #62a)  
**作成日**: 2025-10-17  
**ステータス**: In Progress  

2bykiltのサンドボックス実行機能は、git-script、user-script、browser-controlなどの外部スクリプト実行時にセキュリティ制限を適用し、システムリソースを保護します。

### 主な機能

1. **プロセス分離**: 独立したプロセス空間での実行
2. **リソース制限**: CPU、メモリ、ディスク、プロセス数の制限
3. **システムコール制限**: Linux seccomp-bpfによる危険なシステムコールのブロック
4. **タイムアウト管理**: 長時間実行の防止
5. **実行ログ**: 詳細な実行履歴とリソース使用量の記録

## アーキテクチャ

### コンポーネント構成

```
src/security/
├── sandbox_manager.py      # メインマネージャー
├── syscall_filter.py       # システムコール制限 (Linux)
└── resource_limiter.py     # リソース制限管理 (未実装)

config/
└── feature_flags.yaml      # サンドボックス設定
```

### クラス図

```
┌─────────────────────────┐
│   SandboxManager        │
├─────────────────────────┤
│ + execute()             │
│ + _apply_resource_limits()│
│ + _apply_syscall_filter()│
└──────────┬──────────────┘
           │
           ├── uses ────┐
           │            │
           ▼            ▼
┌──────────────────┐  ┌─────────────────┐
│  SyscallFilter   │  │  SandboxConfig  │
├──────────────────┤  ├─────────────────┤
│ + apply()        │  │ + mode          │
│ + get_profile()  │  │ + limits        │
└──────────────────┘  └─────────────────┘
```

## 実行モード

### モード一覧

| モード | 説明 | 用途 | リソース制限 | syscall制限 |
|--------|------|------|--------------|-------------|
| **STRICT** | 最小限の権限 | 信頼できないスクリプト | ✅ 厳格 | ✅ 最小限のみ |
| **MODERATE** | 標準的な制限 | 一般的なスクリプト | ✅ 標準 | ✅ 一般的なもの |
| **PERMISSIVE** | 緩い制限 | 開発・デバッグ | ✅ 緩い | ✅ ネットワーク以外 |
| **DISABLED** | 制限なし | テスト・ローカル開発 | ❌ なし | ❌ なし |

### モード選択ガイドライン

**STRICT**を使用すべき場合:
- 外部から取得したスクリプト（git-scriptなど）
- 信頼できないユーザーが作成したスクリプト
- 本番環境での実行

**MODERATE**を使用すべき場合:
- 社内で作成・レビューされたスクリプト
- 通常のCI/CDパイプライン
- 標準的な自動化タスク

**PERMISSIVE**を使用すべき場合:
- 開発中のスクリプトのデバッグ
- ローカル環境でのテスト
- 詳細なログ取得が必要な場合

**DISABLED**を使用すべき場合:
- ユニットテスト
- 完全に信頼された環境
- サンドボックスが動作しないプラットフォーム（テスト用）

## リソース制限

### デフォルト制限値

| リソース | STRICT | MODERATE | PERMISSIVE |
|---------|--------|----------|------------|
| **CPU時間** | 60秒 | 300秒 (5分) | 600秒 (10分) |
| **メモリ** | 256MB | 512MB | 1024MB (1GB) |
| **ディスク書き込み** | 50MB | 100MB | 500MB |
| **最大プロセス数** | 5 | 10 | 20 |
| **実行タイムアウト** | 120秒 | 600秒 (10分) | 1200秒 (20分) |

### カスタマイズ

Feature Flagsで制限値をカスタマイズ可能：

```yaml
# config/feature_flags.yaml
security:
  sandbox_enabled: true
  sandbox_mode: "moderate"
  sandbox_resource_limits:
    cpu_time_sec: 300
    memory_mb: 512
    disk_mb: 100
```

プログラムから動的に設定：

```python
from src.security.sandbox_manager import SandboxManager, SandboxConfig, SandboxMode

config = SandboxConfig(
    mode=SandboxMode.STRICT,
    cpu_time_sec=60,
    memory_mb=256,
    timeout_sec=120
)

manager = SandboxManager(config)
result = manager.execute(
    command=["python", "script.py"],
    cwd="/path/to/workdir"
)
```

## システムコール制限 (Linux seccomp)

### プロファイル別許可syscall

#### STRICT プロファイル
基本的なI/O、メモリ管理、プロセス管理のみ:
- ファイルI/O: `read`, `write`, `open`, `close`, `stat`, `fstat`
- メモリ管理: `brk`, `mmap`, `munmap`, `mprotect`
- プロセス: `exit`, `exit_group`, `wait4`
- 情報取得: `getpid`, `getuid`, `gettimeofday`

**許可syscall数**: 約30個

#### MODERATE プロファイル
STRICT + ディレクトリ操作、プロセス/スレッド管理:
- ディレクトリ: `getcwd`, `chdir`, `mkdir`, `rmdir`, `getdents`
- プロセス/スレッド: `clone`, `fork`, `execve`, `vfork`
- リソース管理: `getrlimit`, `setrlimit`

**許可syscall数**: 約70個

#### PERMISSIVE プロファイル
MODERATE + IPC、高度なメモリ操作:
- IPC: メッセージキュー、セマフォ、共有メモリ
- ファイルシステム: `chmod`, `chown`, `link`, `unlink`, `rename`
- メモリ高度操作: `madvise`, `mlock`, `mlockall`

**許可syscall数**: 約100個

### 常に拒否されるsyscall

セキュリティ上の理由から、すべてのプロファイルで以下のsyscallは拒否されます:

| カテゴリ | 拒否syscall | 理由 |
|---------|-------------|------|
| **ネットワーク** | `socket`, `connect`, `bind`, `listen`, `accept` | ネットワークアクセス制御 |
| **システム管理** | `reboot`, `kexec_load`, `mount`, `umount` | システム破壊防止 |
| **セキュリティ** | `ptrace`, `process_vm_readv`, `capset` | デバッグ/攻撃防止 |
| **特権操作** | `setuid`, `setgid`, `setresuid` | 権限昇格防止 |

## プラットフォーム対応

### サポート状況

| プラットフォーム | リソース制限 | syscall制限 | ステータス |
|-----------------|------------|------------|-----------|
| **Linux** | ✅ Full | ✅ seccomp-bpf | Full Support |
| **macOS** | ⚠️ Partial | ❌ N/A | Resource limits only |
| **Windows** | ✅ Job Objects | ❌ N/A | Resource limits via Job Objects |

### Linux環境

**要件**:
- カーネル 3.5+ (seccomp-bpf サポート)
- Python seccomp ライブラリ: `pip install seccomp`

**機能**:
- ✅ 完全なリソース制限 (`resource.setrlimit`)
- ✅ システムコール制限 (seccomp-bpf)
- ✅ プロセス分離
- ✅ タイムアウト管理

### macOS環境

**制限事項**:
- ❌ syscall制限不可（seccomp非サポート）
- ⚠️ `RLIMIT_AS`（メモリ制限）が完全には機能しない場合がある

**利用可能な機能**:
- ✅ CPU時間制限 (`RLIMIT_CPU`)
- ✅ ファイルサイズ制限 (`RLIMIT_FSIZE`)
- ✅ プロセス数制限 (`RLIMIT_NPROC`)
- ✅ タイムアウト管理

### Windows環境

**要件**:
- Windows 7+ (Job Objects サポート)
- Python pywin32 ライブラリ: `pip install pywin32`

**機能**:
- ✅ CPU時間制限（Job Objects）
- ✅ メモリ制限（Job Objects）
- ✅ プロセス数制限（Job Objects）
- ✅ タイムアウト管理
- ✅ プロセス強制終了（Job終了時）

**制限事項**:
- ❌ システムコール制限不可（seccomp非サポート）
- ⚠️ ディスクI/O制限は未実装

**実装詳細**:
- `src/security/windows_job_object.py` - Job Objects ラッパー
- Job Objectsを使用したリソース制限
- CREATE_SUSDENDEDフラグでプロセス作成後にJob割り当て
- JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE で確実な終了

## 使用方法

### 基本的な使用例

```python
from src.security.sandbox_manager import SandboxManager, SandboxConfig

# デフォルト設定（MODERATE）で実行
manager = SandboxManager()

result = manager.execute(
    command=["python", "my_script.py"],
    capture_output=True
)

if result.success:
    print(f"Success! Output: {result.stdout}")
    print(f"Execution time: {result.execution_time:.2f}s")
else:
    print(f"Failed with exit code {result.exit_code}")
    print(f"Errors: {result.stderr}")
```

### Feature Flagsから自動設定

```python
from src.security.sandbox_manager import create_sandbox_from_feature_flags

# config/feature_flags.yaml の設定を自動的に読み込む
manager = create_sandbox_from_feature_flags()

result = manager.execute(
    command=["python", "script.py"],
    cwd="/path/to/workspace"
)
```

### 標準入力の提供

```python
manager = SandboxManager()

result = manager.execute(
    command=["python", "-c", "import sys; print(sys.stdin.read().upper())"],
    stdin_data="hello world",
    capture_output=True
)

print(result.stdout)  # "HELLO WORLD"
```

### カスタム環境変数

```python
from src.security.sandbox_manager import SandboxConfig, SandboxMode

config = SandboxConfig(
    mode=SandboxMode.MODERATE,
    environment_variables={
        "MY_VAR": "custom_value",
        "DEBUG": "true"
    }
)

manager = SandboxManager(config)
result = manager.execute(
    command=["python", "-c", "import os; print(os.environ['MY_VAR'])"],
    capture_output=True
)
```

## セキュリティベストプラクティス

### 1. 適切なモード選択

❌ **避けるべき**:
```python
# 外部スクリプトをDISABLEDで実行
manager = SandboxManager(SandboxConfig(mode=SandboxMode.DISABLED))
result = manager.execute(command=["python", untrusted_script])
```

✅ **推奨**:
```python
# 外部スクリプトはSTRICTで実行
manager = SandboxManager(SandboxConfig(mode=SandboxMode.STRICT))
result = manager.execute(command=["python", untrusted_script])
```

### 2. タイムアウト設定

❌ **避けるべき**:
```python
# 長すぎるタイムアウト
config = SandboxConfig(timeout_sec=3600)  # 1時間
```

✅ **推奨**:
```python
# 適切なタイムアウト
config = SandboxConfig(timeout_sec=300)  # 5分
```

### 3. リソース制限の確認

```python
result = manager.execute(...)

# リソース使用量を確認
print(f"Resources used: {result.resources_used}")

if result.killed:
    print("Warning: Process was killed (timeout or limit exceeded)")
```

### 4. エラーハンドリング

```python
try:
    result = manager.execute(command=["python", "script.py"])
    
    if not result.success:
        logger.error(f"Script failed: {result.stderr}")
        
    if result.killed:
        logger.warning("Script was forcibly terminated")
        
except RuntimeError as e:
    logger.error(f"Sandbox execution failed: {e}")
```

## トラブルシューティング

### 問題: "seccomp library not available"

**原因**: Linux環境でseccompライブラリがインストールされていない

**解決方法**:
```bash
pip install seccomp
```

### 問題: "Exception occurred in preexec_fn"

**原因**: リソース制限の設定値が無効

**解決方法**:
- メモリ制限を緩和する（例: 256MB → 512MB）
- CPU時間制限を確認する
- ログを確認して具体的なエラーを特定

### 問題: macOSでメモリ制限が効かない

**原因**: macOSでは`RLIMIT_AS`が完全にはサポートされていない

**対策**:
- タイムアウトとCPU時間制限を活用
- プロセス数制限で間接的に制御
- 重要な場合はLinux環境を使用

### 問題: Windowsでリソース制限が動作しない

**原因**: Windows版のリソース制限は未実装

**対策**:
- タイムアウト管理を使用
- Issue #62b で Job Objects 実装予定

## 監査とロギング

### 実行ログの取得

すべてのサンドボックス実行は自動的にログに記録されます:

```python
import logging

# ログレベルを設定
logging.basicConfig(level=logging.INFO)

manager = SandboxManager()
result = manager.execute(...)

# ログ出力例:
# INFO: Executing in sandbox: python script.py
# INFO: Execution completed: exit_code=0, time=1.23s, killed=False
```

### 実行結果の分析

```python
result = manager.execute(...)

# 実行情報
print(f"Success: {result.success}")
print(f"Exit code: {result.exit_code}")
print(f"Execution time: {result.execution_time}s")
print(f"Killed: {result.killed}")

# 出力
print(f"STDOUT: {result.stdout}")
print(f"STDERR: {result.stderr}")

# リソース使用量（Unix系のみ）
if result.resources_used:
    print(f"User time: {result.resources_used.get('user_time', 0)}s")
    print(f"System time: {result.resources_used.get('system_time', 0)}s")
    print(f"Max memory: {result.resources_used.get('max_memory_kb', 0)} KB")
```

## パフォーマンス考慮事項

### オーバーヘッド

サンドボックス実行のオーバーヘッド:
- **プロセス起動**: +10-50ms
- **リソース制限設定**: +1-5ms
- **seccomp適用** (Linux): +5-20ms

合計オーバーヘッド: 約20-75ms（実行時間に対して無視できるレベル）

### 推奨設定

**短時間スクリプト** (< 10秒):
```python
config = SandboxConfig(
    mode=SandboxMode.STRICT,
    cpu_time_sec=30,
    timeout_sec=60
)
```

**長時間スクリプト** (数分):
```python
config = SandboxConfig(
    mode=SandboxMode.MODERATE,
    cpu_time_sec=300,
    timeout_sec=600
)
```

## 今後の拡張予定

### Phase #62b - Enforce実装

- [ ] ファイルシステムアクセス制御（allow/denyパス）
- [ ] ネットワークアクセス制御（ホワイトリスト）
- [ ] 実行時監視とアラート
- [ ] Windows Job Objects サポート
- [ ] 監査ログ詳細化

### Issue #52連携

- [ ] パストラバーサル防止
- [ ] 読み書き権限の分離
- [ ] 一時ディレクトリの自動クリーンアップ

## 関連ドキュメント

- [実装計画](../issues/ISSUE_62_IMPLEMENTATION_PLAN.md)
- [セキュリティモデル](SECURITY_MODEL.md)
- [Feature Flags仕様](../feature_flags/FLAGS.md)

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0 | 2025-10-17 | 初版作成（PoC Phase） |

---

**作成者**: 2bykilt Development Team  
**最終更新**: 2025-10-17  
**ステータス**: Draft - In Progress
