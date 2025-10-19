"""
Tests for src/ui/services/playwright_trace_service.py

This module tests Playwright trace viewer session management.
"""

import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.ui.services.playwright_trace_service import (
    TraceViewerSession,
    PlaywrightTraceService,
    ensure_playwright_trace_assets,
    prepare_playwright_trace_session,
    get_playwright_trace_session,
    prune_playwright_trace_sessions
)


@pytest.mark.ci_safe
class TestTraceViewerSession:
    """Tests for TraceViewerSession dataclass."""
    
    def test_session_creation(self, tmp_path):
        """Test creating a trace viewer session."""
        trace_path = tmp_path / "trace.zip"
        created_at = time.time()
        
        session = TraceViewerSession(
            session_id="test-session-123",
            trace_path=trace_path,
            created_at=created_at
        )
        
        assert session.session_id == "test-session-123"
        assert session.trace_path == trace_path
        assert session.created_at == created_at
    
    def test_viewer_url(self, tmp_path):
        """Test generating viewer URL."""
        trace_path = tmp_path / "trace.zip"
        created_at = 1234567890.0
        
        session = TraceViewerSession(
            session_id="abc123",
            trace_path=trace_path,
            created_at=created_at
        )
        
        url = session.viewer_url()
        
        assert "/static/playwright-trace-viewer/index.html" in url
        assert "trace=/trace-viewer/playwright/sessions/abc123/trace.zip" in url
        assert "_cb=1234567890" in url


@pytest.mark.ci_safe
class TestPlaywrightTraceServiceInit:
    """Tests for PlaywrightTraceService initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        service = PlaywrightTraceService()
        
        assert service.asset_dir.exists()
        assert service.session_root.exists()
        assert service._session_ttl_seconds == 1800
        assert service._sessions == {}
    
    def test_init_with_custom_paths(self, tmp_path):
        """Test initialization with custom paths."""
        asset_dir = tmp_path / "assets"
        session_root = tmp_path / "sessions"
        
        service = PlaywrightTraceService(
            asset_dir=asset_dir,
            session_root=session_root,
            session_ttl_seconds=600
        )
        
        assert service.asset_dir == asset_dir.resolve()
        assert service.session_root == session_root.resolve()
        assert service._session_ttl_seconds == 600
        assert session_root.exists()


@pytest.mark.ci_safe
class TestPlaywrightTraceServiceEnsureAssets:
    """Tests for ensure_assets method."""
    
    def test_ensure_assets_first_time(self, tmp_path):
        """Test ensuring assets for the first time."""
        asset_dir = tmp_path / "assets"
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "index.html").write_text("test")
        
        service = PlaywrightTraceService(
            asset_dir=asset_dir,
            asset_source_resolver=lambda: source_dir
        )
        
        result = service.ensure_assets()
        
        assert result == asset_dir
        assert (asset_dir / "index.html").exists()
        assert service._assets_ready is True
    
    def test_ensure_assets_already_ready(self, tmp_path):
        """Test ensuring assets when already ready."""
        asset_dir = tmp_path / "assets"
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "index.html").write_text("test")
        
        service = PlaywrightTraceService(
            asset_dir=asset_dir,
            asset_source_resolver=lambda: source_dir
        )
        
        # First call
        service.ensure_assets()
        
        # Second call should skip copying
        with patch('shutil.copytree') as mock_copy:
            result = service.ensure_assets()
            mock_copy.assert_not_called()
            assert result == asset_dir
    
    def test_ensure_assets_force_refresh(self, tmp_path):
        """Test forcing asset refresh."""
        asset_dir = tmp_path / "assets"
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "index.html").write_text("test")
        
        service = PlaywrightTraceService(
            asset_dir=asset_dir,
            asset_source_resolver=lambda: source_dir
        )
        
        service.ensure_assets()
        
        # Force refresh
        with patch('shutil.copytree') as mock_copy:
            service.ensure_assets(force=True)
            mock_copy.assert_called_once()
    
    def test_ensure_assets_source_not_found(self, tmp_path):
        """Test error when source directory doesn't exist."""
        asset_dir = tmp_path / "assets"
        nonexistent = tmp_path / "nonexistent"
        
        service = PlaywrightTraceService(
            asset_dir=asset_dir,
            asset_source_resolver=lambda: nonexistent
        )
        
        with pytest.raises(RuntimeError, match="source directory not found"):
            service.ensure_assets()


@pytest.mark.ci_safe
class TestPlaywrightTraceServicePrepareSession:
    """Tests for prepare_session method."""
    
    def test_prepare_session_success(self, tmp_path):
        """Test successfully preparing a trace session."""
        asset_dir = tmp_path / "assets"
        session_root = tmp_path / "sessions"
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "index.html").write_text("test")
        
        trace_zip = tmp_path / "input_trace.zip"
        trace_zip.write_bytes(b"mock trace data")
        
        service = PlaywrightTraceService(
            asset_dir=asset_dir,
            session_root=session_root,
            asset_source_resolver=lambda: source_dir
        )
        
        session = service.prepare_session(trace_zip)
        
        assert session.session_id is not None
        assert session.trace_path.exists()
        assert session.trace_path.parent == session_root
        assert session.created_at > 0
    
    def test_prepare_session_file_not_found(self, tmp_path):
        """Test error when trace file doesn't exist."""
        service = PlaywrightTraceService(session_root=tmp_path)
        nonexistent = tmp_path / "nonexistent.zip"
        
        with pytest.raises(FileNotFoundError):
            service.prepare_session(nonexistent)
    
    def test_prepare_session_multiple_sessions(self, tmp_path):
        """Test creating multiple sessions."""
        asset_dir = tmp_path / "assets"
        session_root = tmp_path / "sessions"
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "index.html").write_text("test")
        
        trace1 = tmp_path / "trace1.zip"
        trace1.write_bytes(b"trace 1")
        trace2 = tmp_path / "trace2.zip"
        trace2.write_bytes(b"trace 2")
        
        service = PlaywrightTraceService(
            asset_dir=asset_dir,
            session_root=session_root,
            asset_source_resolver=lambda: source_dir
        )
        
        session1 = service.prepare_session(trace1)
        session2 = service.prepare_session(trace2)
        
        assert session1.session_id != session2.session_id
        assert session1.trace_path.exists()
        assert session2.trace_path.exists()


@pytest.mark.ci_safe
class TestPlaywrightTraceServiceGetSession:
    """Tests for get_session method."""
    
    def test_get_session_exists(self, tmp_path):
        """Test retrieving an existing session."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "index.html").write_text("test")
        
        trace_zip = tmp_path / "trace.zip"
        trace_zip.write_bytes(b"data")
        
        service = PlaywrightTraceService(
            session_root=tmp_path,
            asset_source_resolver=lambda: source_dir
        )
        
        created_session = service.prepare_session(trace_zip)
        retrieved_session = service.get_session(created_session.session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
    
    def test_get_session_not_exists(self, tmp_path):
        """Test retrieving non-existent session."""
        service = PlaywrightTraceService(session_root=tmp_path)
        
        result = service.get_session("nonexistent-id")
        
        assert result is None
    
    def test_get_session_expired(self, tmp_path):
        """Test retrieving expired session."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "index.html").write_text("test")
        
        trace_zip = tmp_path / "trace.zip"
        trace_zip.write_bytes(b"data")
        
        service = PlaywrightTraceService(
            session_root=tmp_path,
            asset_source_resolver=lambda: source_dir,
            session_ttl_seconds=1  # 1 second TTL
        )
        
        session = service.prepare_session(trace_zip)
        
        # Wait for expiration
        time.sleep(1.5)
        
        result = service.get_session(session.session_id)
        
        assert result is None


@pytest.mark.ci_safe
class TestPlaywrightTraceServicePruneSessions:
    """Tests for session pruning."""
    
    def test_prune_expired_sessions(self, tmp_path):
        """Test pruning expired sessions."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "index.html").write_text("test")
        
        trace_zip = tmp_path / "trace.zip"
        trace_zip.write_bytes(b"data")
        
        service = PlaywrightTraceService(
            session_root=tmp_path / "sessions",
            asset_source_resolver=lambda: source_dir,
            session_ttl_seconds=1
        )
        
        session = service.prepare_session(trace_zip)
        session_id = session.session_id
        
        assert service.get_session(session_id) is not None
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Prune sessions
        service.prune_sessions()
        
        assert service.get_session(session_id) is None
    
    def test_prune_keeps_valid_sessions(self, tmp_path):
        """Test that pruning keeps valid sessions."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "index.html").write_text("test")
        
        trace_zip = tmp_path / "trace.zip"
        trace_zip.write_bytes(b"data")
        
        service = PlaywrightTraceService(
            session_root=tmp_path / "sessions",
            asset_source_resolver=lambda: source_dir,
            session_ttl_seconds=3600  # Long TTL
        )
        
        session = service.prepare_session(trace_zip)
        
        # Prune immediately
        service.prune_sessions()
        
        # Session should still exist
        assert service.get_session(session.session_id) is not None


@pytest.mark.ci_safe
class TestGlobalFunctions:
    """Tests for global module-level functions."""
    
    @patch('src.ui.services.playwright_trace_service._default_service')
    def test_ensure_playwright_trace_assets(self, mock_service):
        """Test global ensure_playwright_trace_assets function."""
        mock_service.ensure_assets.return_value = Path("/assets")
        
        result = ensure_playwright_trace_assets(force=True)
        
        mock_service.ensure_assets.assert_called_once_with(force=True)
        assert result == Path("/assets")
    
    @patch('src.ui.services.playwright_trace_service._default_service')
    def test_prepare_playwright_trace_session(self, mock_service, tmp_path):
        """Test global prepare_playwright_trace_session function."""
        trace_zip = tmp_path / "trace.zip"
        mock_session = MagicMock()
        mock_service.prepare_session.return_value = mock_session
        
        result = prepare_playwright_trace_session(trace_zip)
        
        mock_service.prepare_session.assert_called_once_with(trace_zip)
        assert result == mock_session
    
    @patch('src.ui.services.playwright_trace_service._default_service')
    def test_get_playwright_trace_session(self, mock_service):
        """Test global get_playwright_trace_session function."""
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        
        result = get_playwright_trace_session("session-id")
        
        mock_service.get_session.assert_called_once_with("session-id")
        assert result == mock_session
    
    @patch('src.ui.services.playwright_trace_service._default_service')
    def test_prune_playwright_trace_sessions(self, mock_service):
        """Test global prune_playwright_trace_sessions function."""
        prune_playwright_trace_sessions()
        
        mock_service.prune_sessions.assert_called_once()


@pytest.mark.ci_safe
class TestPlaywrightTraceServiceIntegration:
    """Integration tests for PlaywrightTraceService."""
    
    def test_full_session_lifecycle(self, tmp_path):
        """Test complete session lifecycle."""
        asset_dir = tmp_path / "assets"
        session_root = tmp_path / "sessions"
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "index.html").write_text("<html></html>")
        
        trace_zip = tmp_path / "original_trace.zip"
        trace_zip.write_bytes(b"trace content")
        
        service = PlaywrightTraceService(
            asset_dir=asset_dir,
            session_root=session_root,
            asset_source_resolver=lambda: source_dir,
            session_ttl_seconds=2
        )
        
        # Prepare session
        session = service.prepare_session(trace_zip)
        assert session.trace_path.read_bytes() == b"trace content"
        
        # Retrieve session
        retrieved = service.get_session(session.session_id)
        assert retrieved == session
        
        # Check viewer URL
        url = session.viewer_url()
        assert session.session_id in url
        
        # Wait for expiration
        time.sleep(2.5)
        
        # Session should be expired
        expired = service.get_session(session.session_id)
        assert expired is None
