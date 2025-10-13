"""Unit tests for Artifacts Service (Issue #277)

Tests the artifacts listing service layer.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.services.artifacts_service import (
    list_artifacts,
    get_artifact_summary,
    ListArtifactsParams,
    ArtifactItemDTO,
    ArtifactsPage,
)


class TestListArtifacts:
    """Test suite for list_artifacts function."""

    def test_list_artifacts_validation_negative_limit(self):
        """Test that negative limit raises ValueError."""
        params = ListArtifactsParams(limit=-1)
        with pytest.raises(ValueError, match="limit must be non-negative"):
            list_artifacts(params)

    def test_list_artifacts_validation_negative_offset(self):
        """Test that negative offset raises ValueError."""
        params = ListArtifactsParams(offset=-1)
        with pytest.raises(ValueError, match="offset must be non-negative"):
            list_artifacts(params)

    def test_list_artifacts_validation_exceeds_max_limit(self):
        """Test that limit exceeding max raises ValueError."""
        params = ListArtifactsParams(limit=1000)  # Exceeds _MAX_LIMIT=100
        with pytest.raises(ValueError, match="limit must not exceed"):
            list_artifacts(params)

    @patch('src.services.artifacts_service.get_artifacts_base_dir')
    def test_list_artifacts_missing_artifacts_root(self, mock_get_artifacts_base_dir):
        """Test that missing artifacts root raises FileNotFoundError."""
        mock_runs_dir = Mock(spec=Path)
        mock_runs_dir.exists.return_value = False

        mock_base_dir = Mock(spec=Path)
        mock_base_dir.__truediv__ = Mock(return_value=mock_runs_dir)  # Support / operator
        mock_get_artifacts_base_dir.return_value = mock_base_dir

        with pytest.raises(FileNotFoundError, match="Artifacts root does not exist"):
            list_artifacts()

    @patch('src.services.artifacts_service.get_artifacts_base_dir')
    def test_list_artifacts_empty_results(self, mock_get_artifacts_base_dir):
        """Test listing with no manifests returns empty page."""
        mock_runs_dir = Mock(spec=Path)
        mock_runs_dir.exists.return_value = True
        mock_runs_dir.glob.return_value = []  # No manifests found

        mock_artifacts_dir = Mock(spec=Path)
        mock_artifacts_dir.__truediv__ = Mock(return_value=mock_runs_dir)
        mock_get_artifacts_base_dir.return_value = mock_artifacts_dir

        result = list_artifacts()

        assert isinstance(result, ArtifactsPage)
        assert len(result.items) == 0
        assert result.total_count == 0
        assert not result.has_next

    @patch('src.services.artifacts_service.get_artifacts_base_dir')
    def test_list_artifacts_with_run_id_filter(self, mock_get_artifacts_base_dir, tmp_path):
        """Test filtering artifacts by run_id."""
        # Setup: create test manifest
        run_id = "20250113123456-abc123"
        artifacts_root = tmp_path / "runs"
        artifacts_root.mkdir(parents=True)

        manifest_dir = artifacts_root / f"{run_id}-art"
        manifest_dir.mkdir()

        manifest_file = manifest_dir / "manifest_v2.json"
        manifest_data = {
            "schema": "artifact-manifest-v2",
            "run_id": run_id,
            "generated_at": "2025-01-13T12:34:56Z",
            "artifacts": [
                {
                    "type": "screenshot",
                    "path": "screenshots/test.png",
                    "created_at": "2025-01-13T12:34:56Z",
                    "size": 1024,
                    "meta": {"format": "png"},
                }
            ],
        }
        manifest_file.write_text(json.dumps(manifest_data))

        # Create actual artifact file
        screenshot_dir = manifest_dir / "screenshots"
        screenshot_dir.mkdir()
        screenshot_file = screenshot_dir / "test.png"
        screenshot_file.write_bytes(b"fake image data")

        mock_get_artifacts_base_dir.return_value = tmp_path

        # Test with run_id filter
        params = ListArtifactsParams(run_id=run_id, limit=10)
        result = list_artifacts(params)

        assert len(result.items) == 1
        assert result.items[0].run_id == run_id
        assert result.items[0].type == "screenshot"

    @patch('src.services.artifacts_service.get_artifacts_base_dir')
    def test_list_artifacts_with_type_filter(self, mock_get_artifacts_base_dir, tmp_path):
        """Test filtering artifacts by type."""
        # Setup: create test manifest with multiple types
        run_id = "20250113123456-def456"
        artifacts_root = tmp_path / "runs"
        artifacts_root.mkdir(parents=True)

        manifest_dir = artifacts_root / f"{run_id}-art"
        manifest_dir.mkdir()

        manifest_file = manifest_dir / "manifest_v2.json"
        manifest_data = {
            "schema": "artifact-manifest-v2",
            "run_id": run_id,
            "generated_at": "2025-01-13T12:34:56Z",
            "artifacts": [
                {
                    "type": "screenshot",
                    "path": "screenshots/test1.png",
                    "created_at": "2025-01-13T12:34:56Z",
                    "size": 1024,
                },
                {
                    "type": "video",
                    "path": "videos/test.mp4",
                    "created_at": "2025-01-13T12:35:00Z",
                    "size": 2048,
                },
            ],
        }
        manifest_file.write_text(json.dumps(manifest_data))

        # Create artifact files
        screenshot_dir = manifest_dir / "screenshots"
        screenshot_dir.mkdir()
        (screenshot_dir / "test1.png").write_bytes(b"fake image")

        video_dir = manifest_dir / "videos"
        video_dir.mkdir()
        (video_dir / "test.mp4").write_bytes(b"fake video")

        mock_get_artifacts_base_dir.return_value = tmp_path

        # Test with type filter
        params = ListArtifactsParams(artifact_type="screenshot", limit=10)
        result = list_artifacts(params)

        assert len(result.items) == 1
        assert result.items[0].type == "screenshot"

    @patch('src.services.artifacts_service.get_artifacts_base_dir')
    def test_list_artifacts_pagination(self, mock_get_artifacts_base_dir, tmp_path):
        """Test pagination of artifacts."""
        run_id = "20250113123456-ghi789"
        artifacts_root = tmp_path / "runs"
        artifacts_root.mkdir(parents=True)

        manifest_dir = artifacts_root / f"{run_id}-art"
        manifest_dir.mkdir()

        # Create manifest with multiple artifacts
        artifacts_list = []
        for i in range(10):
            artifacts_list.append({
                "type": "screenshot",
                "path": f"screenshots/test{i}.png",
                "created_at": f"2025-01-13T12:34:{i:02d}Z",
                "size": 1024 * (i + 1),
            })

        manifest_file = manifest_dir / "manifest_v2.json"
        manifest_data = {
            "schema": "artifact-manifest-v2",
            "run_id": run_id,
            "generated_at": "2025-01-13T12:34:56Z",
            "artifacts": artifacts_list,
        }
        manifest_file.write_text(json.dumps(manifest_data))

        # Create artifact files
        screenshot_dir = manifest_dir / "screenshots"
        screenshot_dir.mkdir()
        for i in range(10):
            (screenshot_dir / f"test{i}.png").write_bytes(b"fake image")

        mock_get_artifacts_base_dir.return_value = tmp_path

        # Test first page
        params = ListArtifactsParams(limit=5, offset=0)
        result = list_artifacts(params)

        assert len(result.items) == 5
        assert result.has_next is True
        assert result.total_count == 10

        # Test second page
        params = ListArtifactsParams(limit=5, offset=5)
        result = list_artifacts(params)

        assert len(result.items) == 5
        assert result.has_next is False

    @patch('src.services.artifacts_service.get_artifacts_base_dir')
    def test_list_artifacts_recursive_directory_structure(self, mock_get_artifacts_base_dir, tmp_path):
        """Test that artifacts are found recursively in subdirectories."""
        # Setup: create nested directory structure
        artifacts_root = tmp_path / "runs"
        artifacts_root.mkdir(parents=True)

        # Create manifests at different depths
        run_id_1 = "20251013113914-bebd9d"
        run_id_2 = "20251013115335-1f1f33"

        # First run at root level
        manifest_dir_1 = artifacts_root / f"{run_id_1}-art"
        manifest_dir_1.mkdir()
        manifest_path_1 = manifest_dir_1 / "manifest_v2.json"

        screenshot_1 = manifest_dir_1 / "screenshots" / "test1.png"
        screenshot_1.parent.mkdir(parents=True)
        screenshot_1.write_text("fake image 1")

        manifest_1_data = {
            "artifacts": [
                {
                    "type": "screenshot",
                    "path": "screenshots/test1.png",
                    "size": len("fake image 1"),
                    "created_at": "2025-10-13T11:39:14Z",
                }
            ]
        }
        manifest_path_1.write_text(json.dumps(manifest_1_data))

        # Second run also at root level
        manifest_dir_2 = artifacts_root / f"{run_id_2}-art"
        manifest_dir_2.mkdir()
        manifest_path_2 = manifest_dir_2 / "manifest_v2.json"

        element_2 = manifest_dir_2 / "elements" / "element.json"
        element_2.parent.mkdir(parents=True)
        element_2.write_text('{"test": "data"}')

        manifest_2_data = {
            "artifacts": [
                {
                    "type": "element_capture",
                    "path": "elements/element.json",
                    "size": len('{"test": "data"}'),
                    "created_at": "2025-10-13T11:53:35Z",
                }
            ]
        }
        manifest_path_2.write_text(json.dumps(manifest_2_data))

        mock_get_artifacts_base_dir.return_value = tmp_path

        # Test: list all artifacts (should find both recursively)
        result = list_artifacts(ListArtifactsParams(limit=100))

        assert isinstance(result, ArtifactsPage)
        assert result.total_count == 2
        assert len(result.items) == 2

        # Verify both runs are found
        run_ids = {item.run_id for item in result.items}
        assert run_id_1 in run_ids
        assert run_id_2 in run_ids

        # Verify types
        types = {item.type for item in result.items}
        assert "screenshot" in types
        assert "element_capture" in types

    @patch('src.services.artifacts_service.get_artifacts_base_dir')
    def test_list_artifacts_includes_unregistered_txt_csv_files(self, mock_get_artifacts_base_dir, tmp_path):
        """Test that unregistered .txt and .csv files in elements/ are included."""
        artifacts_root = tmp_path / "runs"
        artifacts_root.mkdir(parents=True)

        run_id = "20251013120958-bf067d"
        manifest_dir = artifacts_root / f"{run_id}-art"
        manifest_dir.mkdir()
        manifest_path = manifest_dir / "manifest_v2.json"

        # Create elements directory with various files
        elements_dir = manifest_dir / "elements"
        elements_dir.mkdir()

        # Create .json file (registered in manifest)
        json_file = elements_dir / "element_001.json"
        json_file.write_text('{"test": "data"}')

        # Create .txt files (NOT registered in manifest)
        txt_file_1 = elements_dir / "h1_capture.txt"
        txt_file_1.write_text("TEXT[0]: Example heading")

        txt_file_2 = elements_dir / "articles_capture.txt"
        txt_file_2.write_text("TEXT[0]: Article 1\nTEXT[1]: Article 2")

        # Create .csv file (NOT registered in manifest)
        csv_file = elements_dir / "data_export.csv"
        csv_file.write_text("col1,col2\nval1,val2")

        # Manifest only includes the JSON file
        manifest_data = {
            "artifacts": [
                {
                    "type": "element_capture",
                    "path": "elements/element_001.json",
                    "size": len('{"test": "data"}'),
                    "created_at": "2025-10-13T12:10:33Z",
                }
            ]
        }
        manifest_path.write_text(json.dumps(manifest_data))

        mock_get_artifacts_base_dir.return_value = tmp_path

        # Test: list all element_capture artifacts
        result = list_artifacts(ListArtifactsParams(artifact_type="element_capture", limit=100))

        assert isinstance(result, ArtifactsPage)
        # Should find: 1 json + 2 txt + 1 csv = 4 total
        assert result.total_count == 4
        assert len(result.items) == 4

        # Verify all file types are present
        found_extensions = {Path(item.path).suffix for item in result.items}
        assert ".json" in found_extensions
        assert ".txt" in found_extensions
        assert ".csv" in found_extensions

        # Verify unregistered files have the unregistered flag
        unregistered_items = [item for item in result.items if item.meta and item.meta.get("unregistered")]
        assert len(unregistered_items) == 3  # 2 txt + 1 csv


class TestGetArtifactSummary:
    """Test suite for get_artifact_summary function."""

    @patch('src.services.artifacts_service.list_artifacts')
    def test_get_artifact_summary_empty(self, mock_list_artifacts):
        """Test summary with no artifacts."""
        mock_list_artifacts.return_value = ArtifactsPage(
            items=[],
            limit=0,
            offset=0,
            has_next=False,
            total_count=0,
        )

        result = get_artifact_summary()

        assert result["total"] == 0
        assert result["by_type"]["video"] == 0
        assert result["by_type"]["screenshot"] == 0
        assert result["by_type"]["element_capture"] == 0
        assert result["total_size_bytes"] == 0

    @patch('src.services.artifacts_service.list_artifacts')
    def test_get_artifact_summary_with_data(self, mock_list_artifacts):
        """Test summary with various artifacts."""
        mock_items = [
            ArtifactItemDTO(
                run_id="test1",
                type="video",
                path="/path/to/video.mp4",
                size=1024 * 1024,  # 1 MB
                created_at="2025-01-13T12:00:00Z",
            ),
            ArtifactItemDTO(
                run_id="test1",
                type="screenshot",
                path="/path/to/screenshot.png",
                size=512 * 1024,  # 512 KB
                created_at="2025-01-13T12:01:00Z",
            ),
            ArtifactItemDTO(
                run_id="test1",
                type="screenshot",
                path="/path/to/screenshot2.png",
                size=256 * 1024,  # 256 KB
                created_at="2025-01-13T12:02:00Z",
            ),
            ArtifactItemDTO(
                run_id="test1",
                type="element_capture",
                path="/path/to/element.json",
                size=1024,  # 1 KB
                created_at="2025-01-13T12:03:00Z",
            ),
        ]

        mock_list_artifacts.return_value = ArtifactsPage(
            items=mock_items,
            limit=0,
            offset=0,
            has_next=False,
            total_count=4,
        )

        result = get_artifact_summary()

        assert result["total"] == 4
        assert result["by_type"]["video"] == 1
        assert result["by_type"]["screenshot"] == 2
        assert result["by_type"]["element_capture"] == 1
        expected_size = (1024 * 1024) + (512 * 1024) + (256 * 1024) + 1024
        assert result["total_size_bytes"] == expected_size

    @patch('src.services.artifacts_service.list_artifacts')
    def test_get_artifact_summary_with_error(self, mock_list_artifacts):
        """Test summary when listing fails."""
        mock_list_artifacts.side_effect = Exception("Test error")

        result = get_artifact_summary()

        assert result["total"] == 0
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
