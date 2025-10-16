# Issue #62: 実行サンドボックス機能制限 - 実装計画

## Overview

**Issue Number**: #62  
**Title**: 実行サンドボックス機能制限 (Execution Sandbox Feature Restrictions)  
**Priority**: P0 (High)  
**Phase**: Phase 2  
**Area**: Security  
**Risk**: High  
**Status**: ✅ Phase 2a Complete (Enforce) - 9 Commits  

## Dependencies

- ✅ **Issue #32**: Run/Job ID 基盤 (Completed - PR #79)
- 🔜 **Enables Issue #52**: サンドボックス allow/deny パス

## Implementation Progress

### ✅ Phase 1a: PoC実装 (Completed - 2025-10-17)

**Commits** (7 commits):
- `1fd9a42` - feat(security): Issue #62 - Sandbox manager PoC implementation
- `917ce57` - fix(security): Improve resource limits error handling for macOS
- `82f80e8` - feat(security): Add Linux seccomp-bpf syscall filtering (#62a)
- `ea896e1` - feat(security): Integrate sandbox into git-script execution (#62)
- `8188258` - test(security): Add comprehensive sandbox integration tests (#62)
- `fc32cd4` - fix(test): Fix disabled_mode test to mock Feature Flags
- `a39ab0d` - docs(security): Add comprehensive SANDBOX_SPEC documentation

**Implemented Files**:
- ✅ `src/security/sandbox_manager.py` (600+ lines) - 汎用サンドボックスマネージャー
- ✅ `src/security/syscall_filter.py` (350+ lines) - Linux seccomp-bpf実装
- ✅ `tests/security/test_sandbox_manager.py` (407 lines) - 22テストケース
- ✅ `tests/security/test_syscall_filter.py` (240+ lines) - 15+テストケース
- ✅ `tests/security/test_sandbox_integration_simple.py` (240+ lines) - 8統合テスト
- ✅ `docs/security/SANDBOX_SPEC.md` (500+ lines) - 完全な仕様書
- ✅ `src/utils/git_script_automator.py` (Modified) - サンドボックス統合
- ✅ `config/feature_flags.yaml` (Modified) - サンドボックス設定追加

**Test Results**:
- ✅ 99 tests passed, 8 skipped (Linux-only tests)
- ✅ macOS環境で完全動作確認
- ✅ リソース制限、タイムアウト、環境変数すべて動作
- ✅ Feature Flags統合完了

### ✅ Phase 1b: Windows対応 (Completed - 2025-10-17)

**Commits** (1 commit):
- `7ea5b3f` - feat(security): Add Windows Job Objects support (#62b)

**Implemented Files**:
- ✅ `src/security/windows_job_object.py` (240+ lines) - Windows Job Objects wrapper
- ✅ `tests/security/test_windows_job_object.py` (170+ lines) - 9 Windows専用テスト
- ✅ `requirements.txt` (Modified) - pywin32依存追加

**Windows Features**:
- ✅ CPU時間制限（Job Objects API）
- ✅ メモリ制限（JOB_OBJECT_LIMIT_JOB_MEMORY）
- ✅ プロセス数制限（JOB_OBJECT_LIMIT_ACTIVE_PROCESS）
- ✅ タイムアウト管理
- ✅ CREATE_SUSPENDED + Job assignment + ResumeThread pattern

**Test Results**:
- ✅ 9 Windows専用テスト追加（macOS/Linuxではスキップ）
- ✅ Platform-specific tests with pytest.mark.skipif

**Platform Support**:
- ✅ Linux: Full support (resource limits + seccomp syscall filtering)
- ✅ macOS: Partial support (resource limits only, syscall N/A)
- ✅ Windows: Job Objects support (CPU, memory, process limits)

### ✅ Phase 2a: Enforce実装 (Completed - 2025-10-17)

**Commits** (1 commit):
- `552c482` - feat(security): Issue #62b - Enforce Phase implementation

**Implemented Files**:
- ✅ `src/security/filesystem_access_control.py` (306 lines) - ファイルシステムアクセス制御
- ✅ `src/security/network_access_control.py` (361 lines) - ネットワークアクセス制御
- ✅ `src/security/runtime_monitor.py` (397 lines) - 実行時監視とアラート
- ✅ `src/security/audit_logger.py` (393 lines) - 監査ログ詳細化
- ✅ `tests/security/test_phase2_features.py` (400+ lines) - 24テストケース

**Phase 2 Features**:

1. **Filesystem Access Control** (306 lines)
   - Path traversal detection (../, %2e%2e patterns)
   - Allow/deny path lists with workspace restriction
   - Read-only mode enforcement
   - Sensitive path blocking (/etc/passwd, ~/.ssh/, etc.)
   - System path write protection (/etc/, /usr/, C:\Windows\)

2. **Network Access Control** (361 lines)
   - Host whitelist/blacklist with wildcard support
   - Metadata service blocking (AWS, GCP, Azure)
   - Private IP and localhost filtering
   - Dangerous port detection (SSH, RDP, VNC, etc.)
   - Protocol-level restrictions (HTTP/HTTPS/FTP/etc.)
   - Predefined policies: default, strict, api-only

3. **Runtime Security Monitor** (397 lines)
   - Real-time security event recording
   - Alert threshold with time window (default: 3 events in 5min)
   - Event filtering by type, severity, time range
   - Configurable alert handlers (callback functions)
   - Thread-safe event storage with statistics
   - Critical event immediate alerting

4. **Audit Logger** (393 lines)
   - JSON Lines format audit trail (logs/sandbox_audit.jsonl)
   - Sandbox execution logging with resource usage
   - File/network access event logging
   - Policy violation tracking
   - ISO 8601 timestamps
   - Statistics and recent entry retrieval

**Test Results**:
- ✅ 24 Phase 2 tests (all passed)
- ✅ 123 total security tests passed
- ✅ 17 Windows tests skipped on macOS
- ✅ Comprehensive coverage: path traversal, metadata services, private IPs, alert thresholds

**Total Implementation Statistics**:
- **Total Commits**: 9 (7 Phase 1a + 1 Phase 1b + 1 Phase 2a)
- **Total Lines**: 4,200+ lines (production code + tests + docs)
- **Test Coverage**: 147 test cases (123 passed, 24 phase2)

## Problem Statement

現在、2bykiltには以下のセキュリティ課題があります：

1. **LLM専用サンドボックスのみ**: `src/llm/docker_sandbox.py`はLLM実行に特化しており、汎用的なスクリプト実行には適用されていない
2. **システムコール制限なし**: git-script、browser-control、user-scriptなどの実行時にシステムコール制限がない
3. **ファイルシステムアクセス制限なし**: 任意のファイルシステムアクセスが可能
4. **リソース制限なし**: CPU、メモリ、ディスクI/O制限がない

## Solution Design

### Phase 1: PoC実装 (#62a)

#### 目標
システムコール制限とリソース制限のProof of Conceptを実装し、実行可能性を検証する。

#### 実装内容

1. **汎用サンドボックスマネージャー**
   - ファイル: `src/security/sandbox_manager.py`
   - 機能:
     - プロセス分離（subprocess with security constraints）
     - リソース制限（CPU、メモリ、ディスク）
     - タイムアウト管理
     - 実行ログ記録

2. **システムコール制限（Linux）**
   - seccomp-bpfを使用したシステムコール制限
   - 許可するシステムコール:
     - ファイルI/O: `read`, `write`, `open`, `close`, `stat`, `fstat`
     - メモリ管理: `brk`, `mmap`, `munmap`, `mprotect`
     - プロセス管理: `exit`, `exit_group`, `wait4`
   - 拒否するシステムコール:
     - ネットワーク: `socket`, `connect`, `bind`, `listen`
     - 危険な操作: `ptrace`, `reboot`, `kexec_load`

3. **リソース制限**
   - CPU時間制限（`resource.RLIMIT_CPU`）
   - メモリ制限（`resource.RLIMIT_AS`）
   - ファイルサイズ制限（`resource.RLIMIT_FSIZE`）
   - プロセス数制限（`resource.RLIMIT_NPROC`）

4. **Feature Flag統合**
   - `config/feature_flags.yaml`に以下を追加:
     ```yaml
     security:
       sandbox_enabled: true
       sandbox_mode: "strict"  # strict, moderate, permissive
       sandbox_resource_limits:
         cpu_time_sec: 300
         memory_mb: 512
         disk_mb: 100
     ```

#### 実装ファイル

```
src/security/
├── sandbox_manager.py          # 汎用サンドボックスマネージャー
├── syscall_filter.py           # システムコール制限（seccomp）
├── resource_limiter.py         # リソース制限管理
└── sandbox_config.py           # サンドボックス設定

tests/security/
├── test_sandbox_manager.py
├── test_syscall_filter.py
└── test_resource_limiter.py

docs/security/
└── SANDBOX_SPEC.md             # サンドボックス仕様
```

### Phase 2: Enforce実装 (#62b)

#### 目標
allow/denyリストを実装し、本格的なサンドボックス強制機能を提供する。

#### 実装内容

1. **パス制御（Issue #52連携）**
   - ファイルシステムアクセス制御
   - allow/denyパスリスト
   - パストラバーサル防止

2. **ネットワーク制御**
   - 許可されたホストのみアクセス可能
   - DNS制限
   - プロキシ経由アクセス

3. **実行時監視**
   - システムコール監視
   - リソース使用量モニタリング
   - 異常検知とアラート

4. **監査ログ**
   - すべてのサンドボックス実行を記録
   - セキュリティイベントのトラッキング
   - コンプライアンスレポート生成

## Implementation Strategy

### Step 1: 環境調査とPoC設計 ✅ (Current)
- [x] 既存のDocker sandboxコードを調査
- [x] Linux seccomp, resource limitsの調査
- [x] 実装計画ドキュメント作成

### Step 2: 基本サンドボックス実装
- [ ] `SandboxManager`クラス実装
- [ ] リソース制限機能実装
- [ ] Feature Flag統合

### Step 3: システムコール制限実装（Linux）
- [ ] seccomp-bpfフィルター実装
- [ ] syscallプロファイル定義
- [ ] プラットフォーム検出とフォールバック

### Step 4: 統合とテスト
- [ ] git-script実行時にサンドボックス適用
- [ ] user-script実行時にサンドボックス適用
- [ ] セキュリティテストスイート実装

### Step 5: ドキュメントとPR
- [ ] セキュリティ仕様書作成
- [ ] 運用ガイド作成
- [ ] PR作成とレビュー

## Technical Considerations

### Platform Support

| Platform | seccomp | resource limits | Status |
|----------|---------|-----------------|--------|
| Linux    | ✅ Yes  | ✅ Yes          | Full Support |
| macOS    | ❌ No   | ⚠️ Partial      | Limited (resource only) |
| Windows  | ❌ No   | ⚠️ Partial      | Limited (job objects) |

### Fallback Strategy

1. **Linux**: Full sandbox with seccomp + resource limits
2. **macOS**: Resource limits only (no syscall filtering)
3. **Windows**: Resource limits via job objects
4. **Feature Flag**: Allow disabling sandbox for compatibility

### Security Considerations

1. **Privilege Escalation防止**
   - `PR_SET_NO_NEW_PRIVS` フラグ使用
   - setuid/setgid実行を禁止

2. **情報漏洩防止**
   - 環境変数のフィルタリング
   - シークレットマスキング（Issue #60連携）

3. **DoS攻撃防止**
   - CPU時間制限
   - メモリ制限
   - ファイルディスクリプタ数制限

## Acceptance Criteria

### PoC Phase (#62a)
- [ ] Linux環境でseccomp制限が動作する
- [ ] リソース制限（CPU/Memory）が適用される
- [ ] git-scriptの実行がサンドボックス内で動作する
- [ ] Feature Flagで有効/無効を切り替えられる
- [ ] 基本的なセキュリティテストが通る

### Enforce Phase (#62b)
- [ ] allow/denyパスリストが機能する（Issue #52）
- [ ] ネットワークアクセス制御が動作する
- [ ] 実行時監視とログ記録が動作する
- [ ] 異常検知とアラート機能が動作する
- [ ] すべてのセキュリティテストが通る

## Timeline

- **Week 1**: PoC実装（SandboxManager + resource limits）
- **Week 2**: seccomp実装とテスト
- **Week 3**: 統合テストとドキュメント
- **Week 4**: Enforce機能実装（#62b）

## Related Issues

- **#32**: Run/Job ID 基盤（依存、完了済み）
- **#52**: サンドボックス allow/deny パス（後続）
- **#60**: シークレットマスキング拡張（連携）
- **#61**: 既存依存セキュリティスキャン基盤の最適化（連携）

## References

- 既存実装: `src/llm/docker_sandbox.py`
- セキュリティモデル: `docs/security/SECURITY_MODEL.md`
- Phase4完了レポート: `docs/reviews/phase4-completion-report.md`
- Linux seccomp: https://man7.org/linux/man-pages/man2/seccomp.2.html
- Python resource module: https://docs.python.org/3/library/resource.html

---

**作成日**: 2025-10-17  
**ステータス**: In Progress  
**担当**: TBD  
**レビュー**: Pending
