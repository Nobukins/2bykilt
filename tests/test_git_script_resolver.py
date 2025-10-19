"""
Tests for Git Script Resolver Module

Tests the git_script resolution functionality including:
- Absolute path resolution
- Relative path resolution
- llms.txt lookup resolution
- GitHub repository fetching
- Script validation
- Error handling
"""

import os
import tempfile
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.script.git_script_resolver import GitScriptResolver, GitScriptCandidate, get_git_script_resolver


@pytest.mark.ci_safe
class TestGitScriptResolver:
    """Test cases for GitScriptResolver class"""

    @pytest.fixture
    def resolver(self):
        """Create a GitScriptResolver instance for testing"""
        return GitScriptResolver()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_resolver_initialization(self, resolver):
        """Test that resolver initializes correctly"""
        assert resolver.cache_dir is not None
        assert os.path.exists(resolver.cache_dir)

    @pytest.mark.asyncio
    async def test_resolve_absolute_path_local_file(self, resolver, temp_dir):
        """Test resolving a local file from absolute path"""
        # Create a test file
        test_file = os.path.join(temp_dir, 'test_script.py')
        with open(test_file, 'w') as f:
            f.write('# Test script')

        # Resolve the absolute path
        result = await resolver._resolve_absolute_path(test_file)

        assert result is not None
        assert result['type'] == 'script'
        assert result['script'] == 'test_script.py'
        assert result['resolved_from'] == 'absolute_path'

    @pytest.mark.asyncio
    async def test_resolve_relative_path(self, resolver, temp_dir):
        """Test resolving a script from relative path"""
        # Create a test file in temp directory
        test_file = os.path.join(temp_dir, 'test_script.py')
        with open(test_file, 'w') as f:
            f.write('# Test script')

        # Change to temp directory and test relative path
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = await resolver._resolve_relative_path('test_script.py')

            assert result is not None
            assert result['type'] == 'script'
            assert result['script'] == 'test_script.py'
            assert result['resolved_from'] == 'relative_path'
        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_resolve_from_llms_txt(self, resolver):
        """Test resolving script from llms.txt configuration"""
        with patch('src.config.llms_parser.load_actions_config') as mock_load:
            # Mock llms.txt content with git-script
            mock_load.return_value = {
                'actions': [
                    {
                        'name': 'test-git-script',
                        'type': 'git-script',
                        'git': 'https://github.com/test/repo.git',
                        'script_path': 'scripts/test.py',
                        'version': 'main'
                    }
                ]
            }

            result = await resolver._resolve_from_llms_txt('test-git-script')

            assert result is not None
            assert result['type'] == 'git-script'
            assert result['git'] == 'https://github.com/test/repo.git'
            assert result['script_path'] == 'scripts/test.py'
            assert result['version'] == 'main'
            assert result['resolved_from'] == 'llms.txt'

    @pytest.mark.asyncio
    async def test_resolve_git_script_priority_order(self, resolver, temp_dir):
        """Test that resolution follows the correct priority order"""
        # Create a test file
        test_file = os.path.join(temp_dir, 'test_script.py')
        with open(test_file, 'w') as f:
            f.write('# Test script')

        # Test absolute path (highest priority)
        result = await resolver.resolve_git_script(test_file)
        assert result is not None
        assert result['resolved_from'] == 'absolute_path'

    @pytest.mark.asyncio
    async def test_validate_script_info_valid(self, resolver):
        """Test validation of valid git-script info"""
        script_info = {
            'type': 'git-script',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'scripts/test.py'
        }

        is_valid, error_msg = await resolver.validate_script_info(script_info)

        assert is_valid is True
        assert error_msg == "Valid"

    @pytest.mark.asyncio
    async def test_validate_script_info_invalid_type(self, resolver):
        """Test validation of invalid script type"""
        script_info = {
            'type': 'invalid-type',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'scripts/test.py'
        }

        is_valid, error_msg = await resolver.validate_script_info(script_info)

        assert is_valid is False
        assert "Not a git-script type" in error_msg

    @pytest.mark.asyncio
    async def test_validate_script_info_missing_fields(self, resolver):
        """Test validation with missing required fields"""
        script_info = {
            'type': 'git-script',
            'git': 'https://github.com/test/repo.git'
            # Missing script_path
        }

        is_valid, error_msg = await resolver.validate_script_info(script_info)

        assert is_valid is False
        assert "Missing 'script_path' field" in error_msg

    @pytest.mark.asyncio
    async def test_validate_script_info_invalid_github_url(self, resolver):
        """Test validation with invalid GitHub URL"""
        script_info = {
            'type': 'git-script',
            'git': 'https://not-github.com/test/repo.git',
            'script_path': 'scripts/test.py'
        }

        is_valid, error_msg = await resolver.validate_script_info(script_info)

        assert is_valid is False
        assert "Domain not in allowed list" in error_msg

    @pytest.mark.asyncio
    async def test_validate_script_info_unsafe_path(self, resolver):
        """Test validation with potentially unsafe script path"""
        script_info = {
            'type': 'git-script',
            'git': 'https://github.com/test/repo.git',
            'script_path': '../../../etc/passwd'
        }

        is_valid, error_msg = await resolver.validate_script_info(script_info)

        assert is_valid is False
        assert "Potentially unsafe script path" in error_msg

    @pytest.mark.asyncio
    async def test_get_script_candidates(self, resolver):
        """Test getting script candidates from llms.txt"""
        with patch('src.config.llms_parser.load_actions_config') as mock_load:
            mock_load.return_value = {
                'actions': [
                    {
                        'name': 'test-git-script-1',
                        'type': 'git-script',
                        'git': 'https://github.com/test/repo1.git',
                        'script_path': 'scripts/test1.py'
                    },
                    {
                        'name': 'test-git-script-2',
                        'type': 'git-script',
                        'git': 'https://github.com/test/repo2.git',
                        'script_path': 'scripts/test2.py'
                    },
                    {
                        'name': 'regular-script',
                        'type': 'script',
                        'script': 'regular.py'
                    }
                ]
            }

            candidates = await resolver.get_script_candidates('test')

            assert len(candidates) == 2
            assert all(isinstance(c, GitScriptCandidate) for c in candidates)
            assert candidates[0].name == 'test-git-script-1'
            assert candidates[1].name == 'test-git-script-2'

    @pytest.mark.asyncio
    async def test_fetch_script_from_github_invalid_url(self, resolver):
        """Test fetching script with invalid GitHub URL"""
        result = await resolver.fetch_script_from_github(
            'https://not-github.com/test/repo.git',
            'scripts/test.py'
        )

        assert result is None

    def test_git_script_candidate_repr(self):
        """Test GitScriptCandidate string representation"""
        candidate = GitScriptCandidate(
            name='test-script',
            git_url='https://github.com/test/repo.git',
            script_path='scripts/test.py',
            version='develop'
        )

        repr_str = repr(candidate)
        assert 'test-script' in repr_str
        assert 'https://github.com/test/repo.git' in repr_str
        assert 'scripts/test.py' in repr_str
        assert 'develop' in repr_str

    def test_get_git_script_resolver_singleton(self):
        """Test that get_git_script_resolver returns singleton instance"""
        resolver1 = get_git_script_resolver()
        resolver2 = get_git_script_resolver()

        assert resolver1 is resolver2
        assert isinstance(resolver1, GitScriptResolver)

    @pytest.mark.asyncio
    async def test_resolve_git_script_not_found(self, resolver):
        """Test resolving a non-existent git script"""
        with patch.object(resolver, '_resolve_absolute_path', return_value=None):
            with patch.object(resolver, '_resolve_relative_path', return_value=None):
                with patch.object(resolver, '_resolve_from_llms_txt', return_value=None):
                    result = await resolver.resolve_git_script('non-existent-script')

                    assert result is None

    @pytest.mark.asyncio
    async def test_extract_git_info_from_path_no_git(self, resolver, temp_dir):
        """Test extracting git info from a path that's not in a git repository"""
        test_file = os.path.join(temp_dir, 'test.py')
        with open(test_file, 'w') as f:
            f.write('# Test')

        result = resolver._extract_git_info_from_path(test_file)

        assert result is None

@pytest.mark.ci_safe
class TestAllowedDomains:
    """Test cases for allowed domains functionality (#255)"""

    @pytest.fixture
    def resolver(self):
        """Create a GitScriptResolver instance for testing"""
        return GitScriptResolver()

    def test_is_safe_git_url_github_default(self, resolver):
        """Test that github.com is allowed by default"""
        assert resolver._is_safe_git_url('https://github.com/user/repo.git')
        assert resolver._is_safe_git_url('git@github.com:user/repo.git')

    def test_is_safe_git_url_custom_domain_https(self, resolver, monkeypatch):
        """Test that custom domains can be allowed via environment variable (HTTPS)"""
        with monkeypatch.context() as m:
            m.setenv('GIT_SCRIPT_ALLOWED_DOMAINS', 'github.com,gitlab.example.com')
            # Mock _config to avoid actual file reading
            mock_config = MagicMock(return_value={'git_script': {'allowed_domains': 'github.com'}})
            with patch.object(resolver, '_config', mock_config):
                assert resolver._is_safe_git_url('https://gitlab.example.com/user/repo.git')

    def test_is_safe_git_url_custom_domain_ssh(self, resolver, monkeypatch):
        """Test that custom domains can be allowed via environment variable (SSH)"""
        with monkeypatch.context() as m:
            m.setenv('GIT_SCRIPT_ALLOWED_DOMAINS', 'github.com,gitlab.example.com')
            mock_config = MagicMock(return_value={'git_script': {'allowed_domains': 'github.com'}})
            with patch.object(resolver, '_config', mock_config):
                assert resolver._is_safe_git_url('git@gitlab.example.com:user/repo.git')

    def test_is_safe_git_url_ssh_with_port(self, resolver, monkeypatch):
        """Test SSH URL with port number"""
        with monkeypatch.context() as m:
            m.setenv('GIT_SCRIPT_ALLOWED_DOMAINS', 'github.com,gitlab.example.com')
            mock_config = MagicMock(return_value={'git_script': {'allowed_domains': 'github.com'}})
            with patch.object(resolver, '_config', mock_config):
                assert resolver._is_safe_git_url('git@gitlab.example.com:22:user/repo.git')

    def test_is_safe_git_url_not_in_allowlist(self, resolver):
        """Test that non-allowed domains are rejected"""
        assert not resolver._is_safe_git_url('https://evil.com/user/repo.git')
        assert not resolver._is_safe_git_url('git@evil.com:user/repo.git')

    def test_is_safe_git_url_dangerous_chars(self, resolver):
        """Test that URLs with dangerous characters are rejected"""
        assert not resolver._is_safe_git_url('https://github.com/user;rm -rf /')
        assert not resolver._is_safe_git_url('git@github.com:user|malicious')

    def test_get_allowed_domains_default(self, resolver):
        """Test that default allowed domains returns github.com only"""
        mock_config = MagicMock(return_value={'git_script': {'allowed_domains': 'github.com'}})
        with patch.object(resolver, '_config', mock_config):
            domains = resolver._get_allowed_domains()
            assert 'github.com' in domains

    def test_get_allowed_domains_with_env(self, resolver, monkeypatch):
        """Test that environment variable can add custom domains"""
        with monkeypatch.context() as m:
            m.setenv('GIT_SCRIPT_ALLOWED_DOMAINS', 'github.com,gitlab.example.com,bitbucket.org')
            mock_config = MagicMock(return_value={'git_script': {'allowed_domains': 'github.com'}})
            with patch.object(resolver, '_config', mock_config):
                domains = resolver._get_allowed_domains()
                assert 'github.com' in domains
                assert 'gitlab.example.com' in domains
                assert 'bitbucket.org' in domains

    def test_get_allowed_domains_always_includes_github(self, resolver, monkeypatch):
        """Test that github.com is always included even if not in config"""
        with monkeypatch.context() as m:
            m.setenv('GIT_SCRIPT_ALLOWED_DOMAINS', 'gitlab.example.com')
            mock_config = MagicMock(return_value={'git_script': {'allowed_domains': 'github.com'}})
            with patch.object(resolver, '_config', mock_config):
                domains = resolver._get_allowed_domains()
                assert 'github.com' in domains  # Always included
                assert 'gitlab.example.com' in domains
