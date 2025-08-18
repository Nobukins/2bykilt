"""Unit test for generate_browser_script (pure string generation)."""

from src.script.script_manager import generate_browser_script


def test_generate_browser_script_includes_navigation():
	script_info = {
		"flow": [
			{"action": "navigate", "url": "https://example.com", "wait_until": "domcontentloaded"}
		]
	}
	script = generate_browser_script(script_info, params={})
	assert "page.goto(\"https://example.com\", wait_until=\"domcontentloaded\"" in script

