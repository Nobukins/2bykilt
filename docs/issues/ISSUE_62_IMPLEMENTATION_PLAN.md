# Issue #62: 実行サンドボックス機能制限 - 実装計画

## Overview

**Issue Number**: #62  
**Title**: 実行サンドボックス機能制限 (Execution Sandbox Feature Restrictions)  
**Priority**: P0 (High)  
**Phase**: Phase 2  
**Area**: Security  
**Risk**: High  
**Status**: In Progress  

## Dependencies

- ✅ **Issue #32**: Run/Job ID 基盤 (Completed - PR #79)
- 🔜 **Enables Issue #52**: サンドボックス allow/deny パス

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
