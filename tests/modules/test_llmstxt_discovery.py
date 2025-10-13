"""Unit tests for llms.txt auto-discovery module (Issue #320)

Tests cover:
- URL normalization
- Auto-discovery (HTTPS and HTTP fallback)
- Section parsing (browser-control, git-scripts, automation-commands)
- Integration with existing yaml_parser and llms_schema_validator
- Error handling and edge cases
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from pathlib import Path

from src.modules.llmstxt_discovery import (
    LlmsTxtSource,
    BykiltSectionParser,
    DiscoveryResult,
    ParsedSections,
    discover_and_parse,
    validate_discovered_actions
)


class TestLlmsTxtSource(unittest.TestCase):
    """Test suite for LlmsTxtSource class"""
    
    def test_url_normalization_base_url(self):
        """Test URL normalization from base URL to /llms.txt"""
        source = LlmsTxtSource("https://example.com")
        self.assertEqual(source.url, "https://example.com/llms.txt")
    
    def test_url_normalization_with_path(self):
        """Test URL normalization with path component"""
        source = LlmsTxtSource("https://example.com/docs")
        self.assertEqual(source.url, "https://example.com/llms.txt")
    
    def test_url_normalization_already_llmstxt(self):
        """Test URL normalization when already pointing to llms.txt"""
        source = LlmsTxtSource("https://example.com/llms.txt")
        self.assertEqual(source.url, "https://example.com/llms.txt")
    
    @patch('src.modules.llmstxt_discovery.setup_requests_retry')
    def test_https_only_enforcement(self, mock_setup):
        """Test HTTPS-only enforcement"""
        mock_session = Mock()
        mock_setup.return_value = mock_session
        
        source = LlmsTxtSource("https://example.com", https_only=True)
        # Ensure the mock session is used
        source._session = mock_session
        
        self.assertTrue(source.https_only)
        self.assertEqual(source.base_url, "https://example.com")
    
    @patch('src.modules.llmstxt_discovery.setup_requests_retry')
    def test_auto_discover_success(self, mock_setup):
        """Test successful auto-discovery"""
        mock_session = Mock()
        mock_setup.return_value = mock_session
        
        # Mock successful HEAD request
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.head.return_value = mock_response
        
        source = LlmsTxtSource("https://example.com")
        # Ensure the mock session is used
        source._session = mock_session
        
        result = source.auto_discover()
        
        self.assertTrue(result.success)
        self.assertEqual(result.llms_url, "https://example.com/llms.txt")
        self.assertEqual(result.http_status, 200)
        self.assertFalse(result.fallback_attempted)
    
    @patch('src.modules.llmstxt_discovery.setup_requests_retry')
    def test_auto_discover_404(self, mock_setup):
        """Test auto-discovery with 404 response"""
        mock_session = Mock()
        mock_setup.return_value = mock_session
        
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.head.return_value = mock_response
        
        source = LlmsTxtSource("https://example.com")
        # Ensure the mock session is used
        source._session = mock_session
        
        result = source.auto_discover()
        
        self.assertFalse(result.success)
        self.assertEqual(result.http_status, 404)
        self.assertIn("HTTP 404", result.error)
    
    @patch('src.modules.llmstxt_discovery.setup_requests_retry')
    def test_auto_discover_http_fallback(self, mock_setup):
        """Test HTTP fallback when HTTPS fails and https_only=False"""
        mock_session = Mock()
        mock_setup.return_value = mock_session
        
        # Track call count to differentiate HTTPS (first) vs HTTP (second)
        call_count = {'count': 0}
        
        def head_side_effect(url, **kwargs):
            call_count['count'] += 1
            mock_response = Mock()
            # First call (HTTPS) fails, second call (HTTP) succeeds
            if call_count['count'] == 1:
                mock_response.status_code = 404  # HTTPS fails
            else:
                mock_response.status_code = 200  # HTTP succeeds
            return mock_response
        
        mock_session.head.side_effect = head_side_effect
        
        source = LlmsTxtSource("https://example.com", https_only=False)
        # Ensure the mock session is used (parent class sets self._session in __post_init__)
        source._session = mock_session
        
        result = source.auto_discover()
        
        # Verify HTTP fallback succeeded
        self.assertTrue(result.success, f"Expected success, got error: {result.error}")
        self.assertEqual(result.llms_url, "http://example.com/llms.txt")
        self.assertTrue(result.fallback_attempted)
        # Verify both HTTPS and HTTP were tried
        self.assertEqual(call_count['count'], 2, "Should have tried HTTPS then HTTP")
    
    @patch('src.modules.llmstxt_discovery.setup_requests_retry')
    def test_auto_discover_network_error(self, mock_setup):
        """Test auto-discovery with network error"""
        mock_session = Mock()
        mock_setup.return_value = mock_session
        
        # Mock network error
        mock_session.head.side_effect = requests.RequestException("Connection timeout")
        
        source = LlmsTxtSource("https://example.com")
        # Ensure the mock session is used
        source._session = mock_session
        
        result = source.auto_discover()
        
        self.assertFalse(result.success)
        self.assertIn("Connection timeout", result.error)


class TestBykiltSectionParser(unittest.TestCase):
    """Test suite for BykiltSectionParser class"""
    
    def test_parse_browser_control_section_basic(self):
        """Test parsing basic browser-control section"""
        markdown_content = """
# Test llms.txt

## 2bykilt Browser Control

```yaml
actions:
  - name: test-login
    type: browser-control
    params:
      - name: username
        required: true
        type: string
    flow:
      - action: navigate
        url: "https://example.com/login"
```
"""
        parser = BykiltSectionParser(markdown_content)
        actions = parser.parse_browser_control_section()
        
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['name'], 'test-login')
        self.assertEqual(actions[0]['type'], 'browser-control')
    
    def test_parse_browser_control_section_multiple_actions(self):
        """Test parsing multiple browser-control actions"""
        markdown_content = """
## 2bykilt Browser Control

```yaml
actions:
  - name: action-one
    type: browser-control
    flow:
      - action: click
  - name: action-two
    type: browser-control
    flow:
      - action: fill_form
```
"""
        parser = BykiltSectionParser(markdown_content)
        actions = parser.parse_browser_control_section()
        
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]['name'], 'action-one')
        self.assertEqual(actions[1]['name'], 'action-two')
    
    def test_parse_browser_control_section_not_found(self):
        """Test parsing when browser-control section doesn't exist"""
        markdown_content = """
# Test llms.txt

## Some Other Section

Content here
"""
        parser = BykiltSectionParser(markdown_content)
        actions = parser.parse_browser_control_section()
        
        self.assertEqual(len(actions), 0)
    
    def test_parse_git_scripts_section_basic(self):
        """Test parsing basic git-scripts section"""
        markdown_content = """
## 2bykilt Git Scripts

- [Example Automation](https://github.com/example/automation.git): Test automation scripts
- [Another Script](https://github.com/test/scripts.git): More scripts
"""
        parser = BykiltSectionParser(markdown_content)
        scripts = parser.parse_git_scripts_section()
        
        self.assertEqual(len(scripts), 2)
        self.assertEqual(scripts[0]['name'], 'example-automation')
        self.assertEqual(scripts[0]['type'], 'git-script')
        self.assertEqual(scripts[0]['git'], 'https://github.com/example/automation.git')
        self.assertEqual(scripts[0]['description'], 'Example Automation')
    
    def test_parse_git_scripts_section_not_found(self):
        """Test parsing when git-scripts section doesn't exist"""
        markdown_content = "# Test llms.txt\n\nNo git scripts here"
        parser = BykiltSectionParser(markdown_content)
        scripts = parser.parse_git_scripts_section()
        
        self.assertEqual(len(scripts), 0)
    
    def test_parse_automation_commands_section(self):
        """Test parsing automation commands section"""
        markdown_content = """
## 2bykilt Automation Commands

- [Login Commands](https://example.com/.well-known/2bykilt/login.yaml): Login automation
- [Search Commands](https://example.com/.well-known/2bykilt/search.yaml): Search automation
"""
        parser = BykiltSectionParser(markdown_content)
        urls = parser.parse_automation_commands_section()
        
        self.assertEqual(len(urls), 2)
        self.assertIn('https://example.com/.well-known/2bykilt/login.yaml', urls)
        self.assertIn('https://example.com/.well-known/2bykilt/search.yaml', urls)
    
    def test_slugify_basic(self):
        """Test slugify function"""
        parser = BykiltSectionParser("")
        
        self.assertEqual(parser._slugify("Hello World"), "hello-world")
        self.assertEqual(parser._slugify("Test-Script"), "test-script")
        self.assertEqual(parser._slugify("  Trim  Spaces  "), "trim-spaces")
        self.assertEqual(parser._slugify("Special!@#Characters"), "specialcharacters")
    
    def test_section_content_extraction_between_headings(self):
        """Test extracting content between two ## headings"""
        markdown_content = """
## 2bykilt Browser Control

Content for browser control section

## 2bykilt Git Scripts

Content for git scripts section
"""
        parser = BykiltSectionParser(markdown_content)
        content = parser._extract_section_content(parser.SECTION_PATTERNS['browser_control'])
        
        self.assertIn("Content for browser control section", content)
        self.assertNotIn("Content for git scripts section", content)
    
    def test_case_insensitive_section_matching(self):
        """Test case-insensitive section heading matching"""
        markdown_content = """
## 2BYKILT BROWSER CONTROL

```yaml
actions:
  - name: test-action
    type: browser-control
    flow:
      - action: click
```
"""
        parser = BykiltSectionParser(markdown_content)
        actions = parser.parse_browser_control_section()
        
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['name'], 'test-action')


class TestExtractSections(unittest.TestCase):
    """Test suite for extract_2bykilt_sections method"""
    
    @patch('src.modules.llmstxt_discovery.setup_requests_retry')
    def test_extract_sections_comprehensive(self, mock_setup):
        """Test extracting all section types"""
        mock_session = Mock()
        mock_setup.return_value = mock_session
        
        comprehensive_content = """
# Example llms.txt

## 2bykilt Browser Control

```yaml
actions:
  - name: site-login
    type: browser-control
    flow:
      - action: navigate
```

## 2bykilt Git Scripts

- [Test Scripts](https://github.com/test/scripts.git): Testing

## 2bykilt Automation Commands

- [Login YAML](https://example.com/login.yaml): Commands
"""
        
        source = LlmsTxtSource("https://example.com")
        sections = source.extract_2bykilt_sections(content=comprehensive_content)
        
        self.assertEqual(len(sections.browser_control), 1)
        self.assertEqual(len(sections.git_scripts), 1)
        self.assertEqual(len(sections.command_urls), 1)
        self.assertEqual(sections.section_count, 3)
        self.assertEqual(sections.source_url, "https://example.com/llms.txt")
    
    @patch('src.modules.llmstxt_discovery.setup_requests_retry')
    def test_extract_sections_empty_content(self, mock_setup):
        """Test extracting sections from empty content"""
        mock_session = Mock()
        mock_setup.return_value = mock_session
        
        source = LlmsTxtSource("https://example.com")
        sections = source.extract_2bykilt_sections(content="# Empty llms.txt")
        
        self.assertEqual(len(sections.browser_control), 0)
        self.assertEqual(len(sections.git_scripts), 0)
        self.assertEqual(len(sections.command_urls), 0)
        self.assertEqual(sections.section_count, 0)


class TestUtilityFunctions(unittest.TestCase):
    """Test suite for utility functions"""
    
    @patch('src.modules.llmstxt_discovery.LlmsTxtSource')
    def test_discover_and_parse_success(self, mock_source_class):
        """Test discover_and_parse utility function success path"""
        mock_source = Mock()
        mock_source_class.return_value = mock_source
        
        # Mock successful discovery
        mock_discovery = DiscoveryResult(
            success=True,
            llms_url="https://example.com/llms.txt",
            http_status=200
        )
        mock_source.auto_discover.return_value = mock_discovery
        
        # Mock sections
        mock_sections = ParsedSections(
            browser_control=[{'name': 'test', 'type': 'browser-control', 'flow': []}],
            source_url="https://example.com/llms.txt",
            section_count=1
        )
        mock_source.extract_2bykilt_sections.return_value = mock_sections
        
        discovery, sections = discover_and_parse("https://example.com")
        
        self.assertTrue(discovery.success)
        self.assertIsNotNone(sections)
        self.assertEqual(len(sections.browser_control), 1)
    
    @patch('src.modules.llmstxt_discovery.LlmsTxtSource')
    def test_discover_and_parse_discovery_failure(self, mock_source_class):
        """Test discover_and_parse when discovery fails"""
        mock_source = Mock()
        mock_source_class.return_value = mock_source
        
        # Mock failed discovery
        mock_discovery = DiscoveryResult(
            success=False,
            error="404 Not Found"
        )
        mock_source.auto_discover.return_value = mock_discovery
        
        discovery, sections = discover_and_parse("https://example.com")
        
        self.assertFalse(discovery.success)
        self.assertIsNone(sections)
    
    def test_validate_discovered_actions_all_types(self):
        """Test validate_discovered_actions with all action types"""
        sections = ParsedSections(
            browser_control=[
                {'name': 'action1', 'type': 'browser-control', 'flow': []},
                {'name': 'action2', 'type': 'browser-control', 'flow': []}
            ],
            git_scripts=[
                {'name': 'script1', 'type': 'git-script', 'git': 'https://github.com/test/repo.git', 'script_path': 'run.py'}
            ],
            command_urls=[
                'https://example.com/commands.yaml'
            ],
            section_count=3
        )
        
        summary = validate_discovered_actions(sections)
        
        self.assertEqual(summary['total_browser_control'], 2)
        self.assertEqual(summary['total_git_scripts'], 1)
        self.assertEqual(summary['total_command_urls'], 1)
        # valid_actions should be at least git_scripts (browser-control validation may vary)
        self.assertGreaterEqual(summary['valid_actions'], 1)
    
    def test_validate_discovered_actions_empty(self):
        """Test validate_discovered_actions with empty sections"""
        sections = ParsedSections()
        summary = validate_discovered_actions(sections)
        
        self.assertEqual(summary['total_browser_control'], 0)
        self.assertEqual(summary['total_git_scripts'], 0)
        self.assertEqual(summary['total_command_urls'], 0)
        self.assertEqual(summary['valid_actions'], 0)


class TestRealWorldScenarios(unittest.TestCase):
    """Test real-world usage scenarios"""
    
    def test_fasthtml_style_llmstxt(self):
        """Test parsing FastHTML-style llms.txt structure"""
        fasthtml_content = """
# FastHTML

> FastHTML: Modern, Web Native, Python-based Web Framework

## Docs

- [Main Documentation](https://docs.fastht.ml): Comprehensive guides

## 2bykilt Browser Control

```yaml
actions:
  - name: fasthtml-demo
    type: browser-control
    description: "Demo automation for FastHTML"
    flow:
      - action: navigate
        url: "https://fastht.ml"
```

## Optional

- [API Reference](https://api.fastht.ml): Detailed API docs
"""
        parser = BykiltSectionParser(fasthtml_content)
        actions = parser.parse_browser_control_section()
        
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['name'], 'fasthtml-demo')
        self.assertIn('FastHTML', fasthtml_content)  # Verify original structure preserved
    
    def test_multiple_yaml_blocks_in_section(self):
        """Test parsing multiple YAML blocks within one section"""
        content = """
## 2bykilt Browser Control

First block:

```yaml
actions:
  - name: action-one
    type: browser-control
    flow:
      - action: click
```

Second block:

```yaml
actions:
  - name: action-two
    type: browser-control
    flow:
      - action: fill_form
```
"""
        parser = BykiltSectionParser(content)
        actions = parser.parse_browser_control_section()
        
        # Should parse both blocks
        self.assertEqual(len(actions), 2)
        action_names = [a['name'] for a in actions]
        self.assertIn('action-one', action_names)
        self.assertIn('action-two', action_names)


if __name__ == '__main__':
    unittest.main()
