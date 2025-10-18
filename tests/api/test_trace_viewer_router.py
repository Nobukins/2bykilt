"""
Tests for src/api/trace_viewer_router.py

This module tests Playwright trace viewer session endpoints.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.testclient import TestClient

from src.api.trace_viewer_router import router, serve_playwright_trace


class TestServePlaywrightTrace:
    """Tests for serve_playwright_trace endpoint."""
    
    @patch('src.api.trace_viewer_router.get_playwright_trace_session')
    def test_serve_trace_success(self, mock_get_session):
        """Test successful trace file serving."""
        # Mock session with valid trace path
        mock_session = MagicMock()
        mock_trace_path = MagicMock(spec=Path)
        mock_trace_path.exists.return_value = True
        mock_session.trace_path = mock_trace_path
        mock_get_session.return_value = mock_session
        
        result = serve_playwright_trace("valid-session-id")
        
        assert isinstance(result, FileResponse)
        mock_get_session.assert_called_once_with("valid-session-id")
    
    @patch('src.api.trace_viewer_router.get_playwright_trace_session')
    def test_serve_trace_session_not_found(self, mock_get_session):
        """Test error when session is not found."""
        mock_get_session.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            serve_playwright_trace("nonexistent-session")
        
        assert exc_info.value.status_code == 404
        assert "not found or expired" in exc_info.value.detail
    
    @patch('src.api.trace_viewer_router.get_playwright_trace_session')
    def test_serve_trace_file_missing(self, mock_get_session):
        """Test error when trace file doesn't exist."""
        # Mock session with non-existent trace path
        mock_session = MagicMock()
        mock_trace_path = MagicMock(spec=Path)
        mock_trace_path.exists.return_value = False
        mock_session.trace_path = mock_trace_path
        mock_get_session.return_value = mock_session
        
        with pytest.raises(HTTPException) as exc_info:
            serve_playwright_trace("session-with-missing-file")
        
        assert exc_info.value.status_code == 404
        assert "artifact missing" in exc_info.value.detail
    
    @patch('src.api.trace_viewer_router.get_playwright_trace_session')
    def test_serve_trace_file_response_properties(self, mock_get_session, tmp_path):
        """Test FileResponse properties for trace serving."""
        # Create actual temp trace file
        trace_file = tmp_path / "trace.zip"
        trace_file.write_bytes(b"mock trace data")
        
        mock_session = MagicMock()
        mock_session.trace_path = trace_file
        mock_get_session.return_value = mock_session
        
        result = serve_playwright_trace("session-id")
        
        assert isinstance(result, FileResponse)
        assert result.media_type == "application/zip"
        assert result.filename == "trace.zip"
    
    @patch('src.api.trace_viewer_router.get_playwright_trace_session')
    def test_serve_trace_different_session_ids(self, mock_get_session):
        """Test handling of different session ID formats."""
        mock_session = MagicMock()
        mock_trace_path = MagicMock(spec=Path)
        mock_trace_path.exists.return_value = True
        mock_session.trace_path = mock_trace_path
        mock_get_session.return_value = mock_session
        
        # Test UUID-like ID
        result1 = serve_playwright_trace("123e4567-e89b-12d3-a456-426614174000")
        assert isinstance(result1, FileResponse)
        
        # Test short ID
        result2 = serve_playwright_trace("abc123")
        assert isinstance(result2, FileResponse)
        
        # Test long ID
        result3 = serve_playwright_trace("very-long-session-id-with-many-chars")
        assert isinstance(result3, FileResponse)


class TestTraceViewerRouterIntegration:
    """Integration tests for trace viewer router."""
    
    def test_router_prefix(self):
        """Test that router has correct prefix."""
        assert router.prefix == "/trace-viewer"
    
    def test_router_tags(self):
        """Test that router has correct tags."""
        assert "trace-viewer" in router.tags
    
    @patch('src.api.trace_viewer_router.get_playwright_trace_session')
    def test_endpoint_path(self, mock_get_session, tmp_path):
        """Test that endpoint is accessible at correct path."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        
        # Create test trace file
        trace_file = tmp_path / "test_trace.zip"
        trace_file.write_bytes(b"test data")
        
        mock_session = MagicMock()
        mock_session.trace_path = trace_file
        mock_get_session.return_value = mock_session
        
        client = TestClient(app)
        response = client.get("/trace-viewer/playwright/sessions/test-id/trace.zip")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
    
    @patch('src.api.trace_viewer_router.get_playwright_trace_session')
    def test_endpoint_404_for_missing_session(self, mock_get_session):
        """Test 404 response for missing session."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        
        mock_get_session.return_value = None
        
        client = TestClient(app)
        response = client.get("/trace-viewer/playwright/sessions/missing/trace.zip")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch('src.api.trace_viewer_router.get_playwright_trace_session')
    def test_endpoint_404_for_missing_file(self, mock_get_session, tmp_path):
        """Test 404 response when trace file is missing."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        
        # Mock session with non-existent file
        missing_file = tmp_path / "nonexistent.zip"
        mock_session = MagicMock()
        mock_session.trace_path = missing_file
        mock_get_session.return_value = mock_session
        
        client = TestClient(app)
        response = client.get("/trace-viewer/playwright/sessions/test/trace.zip")
        
        assert response.status_code == 404
        assert "missing" in response.json()["detail"].lower()
    
    @patch('src.api.trace_viewer_router.get_playwright_trace_session')
    def test_content_disposition_header(self, mock_get_session, tmp_path):
        """Test that Content-Disposition header is set correctly."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        
        trace_file = tmp_path / "trace.zip"
        trace_file.write_bytes(b"trace content")
        
        mock_session = MagicMock()
        mock_session.trace_path = trace_file
        mock_get_session.return_value = mock_session
        
        client = TestClient(app)
        response = client.get("/trace-viewer/playwright/sessions/session-123/trace.zip")
        
        assert response.status_code == 200
        # FileResponse should include filename in content-disposition
        assert "trace.zip" in response.headers.get("content-disposition", "")
    
    @patch('src.api.trace_viewer_router.get_playwright_trace_session')
    def test_multiple_concurrent_requests(self, mock_get_session, tmp_path):
        """Test handling of multiple concurrent requests."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        
        # Create test files
        trace1 = tmp_path / "trace1.zip"
        trace1.write_bytes(b"trace 1")
        trace2 = tmp_path / "trace2.zip"
        trace2.write_bytes(b"trace 2")
        
        def get_session_side_effect(session_id):
            session = MagicMock()
            if session_id == "session-1":
                session.trace_path = trace1
            elif session_id == "session-2":
                session.trace_path = trace2
            else:
                return None
            return session
        
        mock_get_session.side_effect = get_session_side_effect
        
        client = TestClient(app)
        
        response1 = client.get("/trace-viewer/playwright/sessions/session-1/trace.zip")
        response2 = client.get("/trace-viewer/playwright/sessions/session-2/trace.zip")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.content == b"trace 1"
        assert response2.content == b"trace 2"
