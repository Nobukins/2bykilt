"""
SyscallFilter テストスイート (Issue #62)

システムコールフィルターの機能テスト。

Note:
    - seccompライブラリが必要（pip install seccomp）
    - Linux専用のテスト（他のOSではスキップ）

作成日: 2025-10-17
"""

import platform
import pytest

from src.security.syscall_filter import (
    SyscallFilter,
    SyscallProfile,
    is_seccomp_available,
    validate_syscall_list
)


@pytest.fixture
def skip_if_not_linux():
    """Linuxでない場合はスキップ"""
    if platform.system() != "Linux":
        pytest.skip("Linux only test")


@pytest.fixture
def skip_if_no_seccomp():
    """seccompが利用できない場合はスキップ"""
    if not is_seccomp_available():
        pytest.skip("seccomp library not available")


class TestSyscallProfile:
    """プロファイル定義のテスト"""
    
    def test_profile_enum_values(self):
        """プロファイル列挙型の値"""
        assert SyscallProfile.STRICT.value == "strict"
        assert SyscallProfile.MODERATE.value == "moderate"
        assert SyscallProfile.PERMISSIVE.value == "permissive"


class TestSyscallFilter:
    """SyscallFilterクラスのテスト"""
    
    def test_initialization_strict(self):
        """STRICT プロファイルでの初期化"""
        filter = SyscallFilter(profile=SyscallProfile.STRICT)
        
        assert filter.profile == SyscallProfile.STRICT
        assert len(filter.allowed_syscalls) > 0
        assert "read" in filter.allowed_syscalls
        assert "write" in filter.allowed_syscalls
        assert "socket" not in filter.allowed_syscalls  # ネットワークは拒否
    
    def test_initialization_moderate(self):
        """MODERATE プロファイルでの初期化"""
        filter = SyscallFilter(profile=SyscallProfile.MODERATE)
        
        assert filter.profile == SyscallProfile.MODERATE
        assert len(filter.allowed_syscalls) > len(SyscallFilter.STRICT_SYSCALLS)
        assert "clone" in filter.allowed_syscalls
        assert "execve" in filter.allowed_syscalls
    
    def test_initialization_permissive(self):
        """PERMISSIVE プロファイルでの初期化"""
        filter = SyscallFilter(profile=SyscallProfile.PERMISSIVE)
        
        assert filter.profile == SyscallProfile.PERMISSIVE
        assert len(filter.allowed_syscalls) > len(SyscallFilter.MODERATE_SYSCALLS)
    
    def test_custom_allowed_syscalls(self):
        """カスタム許可syscalls"""
        custom_allowed = ["custom_syscall_123"]
        filter = SyscallFilter(
            profile=SyscallProfile.STRICT,
            custom_allowed=custom_allowed
        )
        
        assert "custom_syscall_123" in filter.allowed_syscalls
    
    def test_custom_denied_syscalls(self):
        """カスタム拒否syscalls"""
        filter = SyscallFilter(
            profile=SyscallProfile.MODERATE,
            custom_denied=["clone"]  # cloneを拒否
        )
        
        assert "clone" not in filter.allowed_syscalls
    
    def test_always_denied_syscalls(self):
        """常に拒否されるsyscalls"""
        filter = SyscallFilter(profile=SyscallProfile.PERMISSIVE)
        
        # 危険なsyscallは常に拒否
        assert "socket" not in filter.allowed_syscalls
        assert "reboot" not in filter.allowed_syscalls
        assert "ptrace" not in filter.allowed_syscalls
        assert "mount" not in filter.allowed_syscalls
    
    def test_get_profile_info(self):
        """プロファイル情報の取得"""
        filter = SyscallFilter(profile=SyscallProfile.MODERATE)
        info = filter.get_profile_info()
        
        assert info["profile"] == "moderate"
        assert "platform" in info
        assert "allowed_count" in info
        assert "denied_count" in info
        assert isinstance(info["supported"], bool)


@pytest.mark.skipif(
    platform.system() != "Linux",
    reason="Linux only test"
)
class TestSyscallFilterLinux:
    """Linux環境でのテスト"""
    
    def test_apply_on_linux_without_seccomp(self, skip_if_not_linux):
        """seccompなしでの適用（警告のみ）"""
        filter = SyscallFilter(profile=SyscallProfile.MODERATE)
        # seccompがなくてもエラーにならない
        result = filter.apply()
        # seccompライブラリがない場合はFalse
        assert isinstance(result, bool)
    
    @pytest.mark.skipif(
        not is_seccomp_available(),
        reason="seccomp library required"
    )
    def test_apply_with_seccomp(self, skip_if_no_seccomp):
        """seccompライブラリがある場合の適用"""
        filter = SyscallFilter(profile=SyscallProfile.MODERATE)
        
        # Note: 実際のseccomp適用はテストプロセス全体に影響するため、
        # ここでは適用をシミュレートするのみ
        # 実際の適用テストは統合テストで行う
        info = filter.get_profile_info()
        assert info["supported"] == True


class TestUtilityFunctions:
    """ユーティリティ関数のテスト"""
    
    def test_is_seccomp_available(self):
        """seccomp利用可能性チェック"""
        result = is_seccomp_available()
        assert isinstance(result, bool)
        
        if platform.system() == "Linux":
            # Linuxでは True または False（ライブラリの有無）
            pass
        else:
            # Linux以外では必ずFalse
            assert result == False
    
    def test_validate_syscall_list_non_linux(self):
        """非Linux環境でのsyscall検証"""
        if platform.system() != "Linux":
            syscalls = ["read", "write", "invalid_syscall"]
            valid, invalid = validate_syscall_list(syscalls)
            
            # Linux以外では検証できない
            assert valid == []
            assert invalid == syscalls
    
    @pytest.mark.skipif(
        not is_seccomp_available(),
        reason="seccomp library required"
    )
    def test_validate_syscall_list_with_seccomp(self, skip_if_no_seccomp):
        """seccompを使用したsyscall検証"""
        syscalls = ["read", "write", "invalid_syscall_xyz"]
        valid, invalid = validate_syscall_list(syscalls)
        
        assert "read" in valid
        assert "write" in valid
        assert "invalid_syscall_xyz" in invalid


class TestPreexecFn:
    """preexec_fn生成のテスト"""
    
    def test_create_preexec_fn(self):
        """preexec_fn関数の生成"""
        preexec_fn = SyscallFilter.create_preexec_fn(
            profile=SyscallProfile.STRICT
        )
        
        assert callable(preexec_fn)
    
    def test_create_preexec_fn_with_custom(self):
        """カスタム設定付きpreexec_fn"""
        preexec_fn = SyscallFilter.create_preexec_fn(
            profile=SyscallProfile.MODERATE,
            custom_allowed=["custom1"],
            custom_denied=["clone"]
        )
        
        assert callable(preexec_fn)


@pytest.mark.integration
@pytest.mark.skipif(
    not is_seccomp_available(),
    reason="seccomp library required"
)
class TestSeccompIntegration:
    """seccomp統合テスト（Linux + seccompライブラリ）"""
    
    def test_seccomp_filter_creation(self, skip_if_no_seccomp):
        """seccompフィルターの作成"""
        import seccomp
        
        # フィルター作成テスト
        f = seccomp.SyscallFilter(defaction=seccomp.ERRNO(1))
        assert f is not None
    
    def test_syscall_resolution(self, skip_if_no_seccomp):
        """システムコール名の解決"""
        import seccomp
        
        # 基本的なsyscallの解決
        read_num = seccomp.resolve_syscall("read")
        assert isinstance(read_num, int)
        assert read_num >= 0
        
        write_num = seccomp.resolve_syscall("write")
        assert isinstance(write_num, int)
        assert write_num >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
