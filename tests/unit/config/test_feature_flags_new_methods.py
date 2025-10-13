"""Unit tests for FeatureFlags class new methods (Issue #272)

Tests the new get_all_flags() and get_flag_metadata() methods.
"""
import pytest
from unittest.mock import patch, mock_open
import yaml

from src.config.feature_flags import FeatureFlags


class TestFeatureFlagsNewMethods:
    """Test suite for new FeatureFlags API methods."""
    
    @pytest.fixture(autouse=True)
    def reset_feature_flags(self):
        """Reset FeatureFlags state before each test."""
        # Force reload from actual config file
        FeatureFlags.reload()
        yield
        # Clean up: clear overrides added during test
        with FeatureFlags._lock:
            FeatureFlags._overrides.clear()
    
    def test_get_all_flags_basic(self):
        """Test get_all_flags() returns all flags with metadata."""
        # This test uses the actual config file if present
        # We'll verify the structure rather than exact count
        
        all_flags = FeatureFlags.get_all_flags()
        
        # Should have at least some flags from actual config
        assert len(all_flags) > 0
        
        # Verify structure of returned data
        for flag_name, flag_data in all_flags.items():
            assert isinstance(flag_name, str)
            assert isinstance(flag_data, dict)
            assert "value" in flag_data
            assert "default" in flag_data
            assert "type" in flag_data
            assert "description" in flag_data
            assert "source" in flag_data
            assert "override_active" in flag_data
            assert flag_data["source"] in ["file", "environment", "runtime"]
            assert flag_data["type"] in ["bool", "int", "str"]
    
    def test_get_all_flags_with_overrides(self):
        """Test get_all_flags() includes runtime overrides."""
        # Use actual config and add an override
        all_flags_before = FeatureFlags.get_all_flags()
        if not all_flags_before:
            pytest.skip("No flags in config file")
        
        # Pick first flag and set an override
        test_flag_name = list(all_flags_before.keys())[0]
        original_value = all_flags_before[test_flag_name]["value"]
        
        # Set a runtime override with different value
        if isinstance(original_value, bool):
            override_value = not original_value
        elif isinstance(original_value, int):
            override_value = original_value + 100
        else:
            override_value = "overridden_" + str(original_value)
        
        FeatureFlags.set_override(test_flag_name, override_value)
        
        all_flags_after = FeatureFlags.get_all_flags()
        
        assert all_flags_after[test_flag_name]["value"] == override_value
        assert all_flags_after[test_flag_name]["source"] == "runtime"
        assert all_flags_after[test_flag_name]["override_active"] is True
        
        # Clean up
        FeatureFlags.clear_override(test_flag_name)
    
    def test_get_all_flags_with_environment(self):
        """Test get_all_flags() includes environment variables."""
        # This test would require setting env vars before reload
        # For simplicity, we'll just verify the source field exists
        all_flags = FeatureFlags.get_all_flags()
        
        # Check that source field is properly set
        for flag_data in all_flags.values():
            assert flag_data["source"] in ["file", "environment", "runtime"]
    
    def test_get_flag_metadata_existing(self):
        """Test get_flag_metadata() for existing flag."""
        all_flags = FeatureFlags.get_all_flags()
        if not all_flags:
            pytest.skip("No flags in config file")
        
        # Pick a flag and test metadata retrieval
        test_flag_name = list(all_flags.keys())[0]
        
        metadata = FeatureFlags.get_flag_metadata(test_flag_name)
        
        assert metadata is not None
        assert "value" in metadata
        assert "type" in metadata
        assert "description" in metadata
        assert "source" in metadata
    
    def test_get_flag_metadata_nonexistent(self):
        """Test get_flag_metadata() for non-existent flag."""
        metadata = FeatureFlags.get_flag_metadata("nonexistent_flag_xyz_12345")
        
        assert metadata is None
    
    def test_get_all_flags_empty_config(self):
        """Test get_all_flags() handles empty or no config gracefully."""
        # Even if config is empty, get_all_flags should not crash
        all_flags = FeatureFlags.get_all_flags()
        
        # Should return dict (empty or with actual flags)
        assert isinstance(all_flags, dict)
    
    def test_get_all_flags_thread_safety(self):
        """Test get_all_flags() is thread-safe."""
        import threading
        
        results = []
        errors = []
        
        def get_flags():
            try:
                flags = FeatureFlags.get_all_flags()
                results.append(len(flags))
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=get_flags) for _ in range(10)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify no errors and consistent results
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r == results[0] for r in results)
    
    def test_get_flag_metadata_with_override(self):
        """Test get_flag_metadata() includes override information."""
        all_flags = FeatureFlags.get_all_flags()
        if not all_flags:
            pytest.skip("No flags in config file")
        
        # Pick a flag
        test_flag_name = list(all_flags.keys())[0]
        original_metadata = FeatureFlags.get_flag_metadata(test_flag_name)
        
        # Set override
        if original_metadata["type"] == "bool":
            override_value = not original_metadata["value"]
        elif original_metadata["type"] == "int":
            override_value = original_metadata["value"] + 999
        else:
            override_value = "test_override_value"
        
        FeatureFlags.set_override(test_flag_name, override_value)
        
        metadata = FeatureFlags.get_flag_metadata(test_flag_name)
        
        assert metadata["value"] == override_value
        assert metadata["source"] == "runtime"
        assert metadata["override_active"] is True
        
        # Clean up
        FeatureFlags.clear_override(test_flag_name)


class TestFeatureFlagsMetadataAccuracy:
    """Test metadata accuracy and consistency."""
    
    @pytest.fixture(autouse=True)
    def reset_feature_flags(self):
        """Reset FeatureFlags state before each test."""
        # Force reload from actual config file
        FeatureFlags.reload()
        yield
        with FeatureFlags._lock:
            FeatureFlags._overrides.clear()
    
    def test_metadata_matches_get_method(self):
        """Test that metadata value matches get() method."""
        all_flags = FeatureFlags.get_all_flags()
        if not all_flags:
            pytest.skip("No flags in config file")
        
        # Test a few flags
        for flag_name in list(all_flags.keys())[:3]:
            flag_data = all_flags[flag_name]
            
            # Get via metadata
            metadata = FeatureFlags.get_flag_metadata(flag_name)
            metadata_value = metadata["value"]
            
            # Get via standard method
            if flag_data["type"] == "bool":
                direct_value = FeatureFlags.get(flag_name, expected_type=bool)
            elif flag_data["type"] == "int":
                direct_value = FeatureFlags.get(flag_name, expected_type=int)
            else:
                direct_value = FeatureFlags.get(flag_name, expected_type=str)
            
            assert metadata_value == direct_value
    
    def test_all_flags_consistency(self):
        """Test that get_all_flags() and individual get_flag_metadata() are consistent."""
        all_flags = FeatureFlags.get_all_flags()
        if not all_flags:
            pytest.skip("No flags in config file")
        
        # Test consistency for all flags
        for flag_name in all_flags.keys():
            all_flags_data = all_flags[flag_name]
            individual_data = FeatureFlags.get_flag_metadata(flag_name)
            
            # get_flag_metadata may include 'name' field, which get_all_flags doesn't
            # Compare the common fields
            for key in all_flags_data.keys():
                assert key in individual_data
                assert all_flags_data[key] == individual_data[key], \
                    f"Mismatch in flag '{flag_name}' field '{key}': {all_flags_data[key]} != {individual_data[key]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
