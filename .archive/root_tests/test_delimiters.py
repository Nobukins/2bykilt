"""Test parameter placeholder substitution in script generation."""

from src.script.script_manager import generate_browser_script


def test_generate_replaces_param_placeholders():
	script_info = {
		"flow": [
			{"action": "navigate", "url": "${params.base_url}/path"}
		]
	}
	script = generate_browser_script(script_info, params={"base_url": "https://example.com"})
	assert "https://example.com/path" in script

