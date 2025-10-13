"""llms.txt Auto-Discovery Module (Issue #320)

This module provides auto-discovery and import functionality for browser automation 
commands from remote llms.txt files. It implements the llms.txt standard 
(https://llmstxt.org/) with 2bykilt-specific extensions.

Key Features:
- Auto-discovery of /llms.txt from base URLs
- 2bykilt section detection (Browser Control, Git Scripts, Automation Commands)
- YAML/Markdown parsing with existing validators
- HTTPS enforcement and security validation
- Caching and retry support

Architecture:
- LlmsTxtSource: Auto-discovery and fetching (extends YamlInstructionSource)
- BykiltSectionParser: 2bykilt-specific section parsing
- Integration with existing yaml_parser.py and llms_schema_validator.py
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse, urljoin
import requests

from src.modules.yaml_parser import (
    YamlInstructionSource,
    MarkdownYamlParser,
    setup_requests_retry
)
from src.config.llms_schema_validator import validate_llms_actions, LLMSSchemaValidationError

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Result of llms.txt discovery operation"""
    success: bool
    llms_url: Optional[str] = None
    error: Optional[str] = None
    http_status: Optional[int] = None
    fallback_attempted: bool = False


@dataclass
class ParsedSections:
    """Parsed 2bykilt sections from llms.txt"""
    browser_control: List[Dict[str, Any]] = field(default_factory=list)
    git_scripts: List[Dict[str, Any]] = field(default_factory=list)
    command_urls: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    section_count: int = 0


class LlmsTxtSource(YamlInstructionSource):
    """Extended YamlInstructionSource with llms.txt auto-discovery
    
    Provides auto-discovery of /llms.txt from base URLs and 2bykilt section extraction.
    Inherits caching and retry logic from YamlInstructionSource.
    """
    
    def __init__(
        self, 
        url: str,
        cache_ttl: int = 3600,
        retry_count: int = 3,
        https_only: bool = True
    ):
        """Initialize LlmsTxtSource
        
        Args:
            url: Base URL or full llms.txt URL
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
            retry_count: Number of retry attempts
            https_only: Enforce HTTPS URLs only (default: True for security)
        """
        # Normalize URL to llms.txt if not already
        normalized_url = self._normalize_llms_url(url)
        super().__init__(
            url=normalized_url,
            cache_ttl=cache_ttl,
            retry_count=retry_count
        )
        self.https_only = https_only
        self.base_url = url
    
    def _normalize_llms_url(self, url: str) -> str:
        """Normalize URL to point to /llms.txt
        
        Args:
            url: Base URL (https://example.com or https://example.com/path)
            
        Returns:
            Full llms.txt URL (https://example.com/llms.txt)
        """
        if url.endswith('/llms.txt'):
            return url
        
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/llms.txt"
    
    def auto_discover(self, base_url: Optional[str] = None) -> DiscoveryResult:
        """Auto-discover llms.txt from base URL
        
        Attempts to find llms.txt at the root of the domain. If https_only is False,
        will fallback to HTTP if HTTPS fails.
        
        Args:
            base_url: Base URL to discover from (uses self.base_url if not provided)
            
        Returns:
            DiscoveryResult with discovery status and llms.txt URL if found
        """
        target_url = base_url or self.base_url
        llms_url = self._normalize_llms_url(target_url)
        
        logger.info(f"Auto-discovering llms.txt from: {llms_url}")
        
        # Try HTTPS first
        result = self._try_discovery(llms_url)
        if result.success:
            logger.info(f"✓ Found llms.txt at: {llms_url}")
            return result
        
        # Fallback to HTTP if HTTPS-only not enforced
        if not self.https_only and llms_url.startswith('https://'):
            http_url = llms_url.replace('https://', 'http://', 1)
            logger.info(f"HTTPS failed, trying HTTP fallback: {http_url}")
            http_result = self._try_discovery(http_url)
            if http_result.success:
                logger.warning(f"⚠ Found llms.txt via HTTP (insecure): {http_url}")
                http_result.fallback_attempted = True
                return http_result
            # If HTTP also fails, return the HTTP result
            # Combine HTTPS and HTTP error details for debugging
            combined_error = (
                f"HTTPS attempt failed: {result.error or 'Unknown error'}; "
                f"HTTP attempt failed: {http_result.error or 'Unknown error'}"
            )
            # Return a DiscoveryResult with combined error info
            result = DiscoveryResult(
                success=False,
                llms_url=http_result.llms_url,
                error=combined_error,
                http_status=http_result.http_status,
                fallback_attempted=True
            )
        
        logger.warning(f"✗ llms.txt not found at: {target_url}")
        return result
    
    def _try_discovery(self, url: str) -> DiscoveryResult:
        """Try to discover llms.txt at specific URL
        
        Args:
            url: Full llms.txt URL to try
            
        Returns:
            DiscoveryResult with discovery status
        """
        try:
            # Use HEAD request for efficient discovery
            response = self._session.head(url, timeout=5, allow_redirects=True)
            
            if response.status_code == 200:
                return DiscoveryResult(
                    success=True,
                    llms_url=url,
                    http_status=200
                )
            else:
                return DiscoveryResult(
                    success=False,
                    error=f"HTTP {response.status_code}",
                    http_status=response.status_code
                )
        except requests.RequestException as e:
            logger.debug(f"Discovery failed for {url}: {e}")
            return DiscoveryResult(
                success=False,
                error=str(e)
            )
    
    def extract_2bykilt_sections(self, content: Optional[str] = None) -> ParsedSections:
        """Extract 2bykilt-specific sections from llms.txt content
        
        Detects and parses the following sections:
        - ## 2bykilt Browser Control (YAML blocks with browser-control actions)
        - ## 2bykilt Git Scripts (Markdown links to GitHub repos)
        - ## 2bykilt Automation Commands (Markdown links to external YAML files)
        
        Args:
            content: Raw llms.txt content (fetches if not provided)
            
        Returns:
            ParsedSections with extracted actions and metadata
        """
        if content is None:
            try:
                content = self.fetch()
            except Exception as e:
                logger.error(f"Failed to fetch content for section extraction: {e}")
                return ParsedSections()
        
        parser = BykiltSectionParser(content)
        sections = ParsedSections(source_url=self.url)
        
        # Extract browser-control section
        sections.browser_control = parser.parse_browser_control_section()
        logger.info(f"Found {len(sections.browser_control)} browser-control actions")
        
        # Extract git-script section
        sections.git_scripts = parser.parse_git_scripts_section()
        logger.info(f"Found {len(sections.git_scripts)} git-script definitions")
        
        # Extract automation command URLs
        sections.command_urls = parser.parse_automation_commands_section()
        logger.info(f"Found {len(sections.command_urls)} automation command URLs")
        
        sections.section_count = sum([
            1 if sections.browser_control else 0,
            1 if sections.git_scripts else 0,
            1 if sections.command_urls else 0
        ])
        
        return sections


class BykiltSectionParser:
    """Parser for 2bykilt-specific sections in llms.txt
    
    Implements parsing logic for three types of 2bykilt sections:
    1. Browser Control: YAML blocks with browser-control actions
    2. Git Scripts: Markdown links to GitHub repositories
    3. Automation Commands: Markdown links to external YAML files
    """
    
    # Section pattern definitions (case-insensitive)
    SECTION_PATTERNS = {
        'browser_control': r'##\s+2bykilt\s+Browser\s+Control',
        'git_scripts': r'##\s+2bykilt\s+Git\s+Scripts',
        'automation_commands': r'##\s+2bykilt\s+Automation\s+Commands'
    }
    
    def __init__(self, markdown_content: str):
        """Initialize parser with markdown content
        
        Args:
            markdown_content: Raw markdown content from llms.txt
        """
        self.markdown_content = markdown_content
    
    def _extract_section_content(self, section_pattern: str) -> Optional[str]:
        """Extract content between a section heading and the next heading
        
        Args:
            section_pattern: Regex pattern for section heading
            
        Returns:
            Section content between heading and next ## heading (or EOF)
        """
        # Find section start
        match = re.search(section_pattern, self.markdown_content, re.IGNORECASE)
        if not match:
            return None
        
        start_pos = match.end()
        
        # Find next section (##) or end of document
        next_section = re.search(r'\n##\s+', self.markdown_content[start_pos:])
        if next_section:
            end_pos = start_pos + next_section.start()
        else:
            end_pos = len(self.markdown_content)
        
        return self.markdown_content[start_pos:end_pos].strip()
    
    def parse_browser_control_section(self) -> List[Dict[str, Any]]:
        """Extract browser-control actions from YAML blocks
        
        Parses YAML code blocks in the "## 2bykilt Browser Control" section
        and validates them using existing llms_schema_validator.
        
        Returns:
            List of validated browser-control action dictionaries
        """
        section_content = self._extract_section_content(
            self.SECTION_PATTERNS['browser_control']
        )
        
        if not section_content:
            logger.debug("No '2bykilt Browser Control' section found")
            return []
        
        # Use existing MarkdownYamlParser to extract YAML blocks
        yaml_parser = MarkdownYamlParser(section_content)
        yaml_blocks = yaml_parser.parse_yaml_blocks()
        
        validated_actions = []
        
        for block in yaml_blocks:
            if isinstance(block, dict) and 'actions' in block:
                # Validate entire actions block
                try:
                    actions = validate_llms_actions(block, strict=False)
                    # Filter for browser-control type
                    browser_actions = [
                        action for action in actions 
                        if action.get('type') == 'browser-control'
                    ]
                    validated_actions.extend(browser_actions)
                except LLMSSchemaValidationError as e:
                    logger.warning(f"Validation error in browser-control section: {e}")
            elif isinstance(block, dict) and block.get('type') == 'browser-control':
                # Single action without 'actions' wrapper
                try:
                    validated = validate_llms_actions({'actions': [block]}, strict=False)
                    if validated:
                        validated_actions.append(validated[0])
                except LLMSSchemaValidationError as e:
                    logger.warning(f"Validation error for action: {e}")
        
        return validated_actions
    
    def parse_git_scripts_section(self) -> List[Dict[str, Any]]:
        """Extract git-script URLs from markdown links
        
        Parses markdown links in the "## 2bykilt Git Scripts" section and
        converts them to git-script action format.
        
        Returns:
            List of git-script action dictionaries
        """
        section_content = self._extract_section_content(
            self.SECTION_PATTERNS['git_scripts']
        )
        
        if not section_content:
            logger.debug("No '2bykilt Git Scripts' section found")
            return []
        
        # Extract markdown links: [title](url)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        links = re.findall(link_pattern, section_content)
        
        git_scripts = []
        for title, url in links:
            # Check if URL is GitHub/Git repository
            if 'github.com' in url or url.endswith('.git'):
                script_name = self._slugify(title)
                git_scripts.append({
                    'name': script_name,
                    'type': 'git-script',
                    'git': url,
                    'script_path': 'run.py',  # Default, can be overridden
                    'description': title,
                    'source': 'llms.txt auto-import'
                })
                logger.debug(f"Found git-script: {script_name} -> {url}")
        
        return git_scripts
    
    def parse_automation_commands_section(self) -> List[str]:
        """Extract automation command URLs from markdown links
        
        Parses markdown links in the "## 2bykilt Automation Commands" section.
        These URLs point to external YAML files that can be recursively fetched.
        
        Returns:
            List of absolute URLs to external YAML files
        """
        section_content = self._extract_section_content(
            self.SECTION_PATTERNS['automation_commands']
        )
        
        if not section_content:
            logger.debug("No '2bykilt Automation Commands' section found")
            return []
        
        # Extract markdown links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        links = re.findall(link_pattern, section_content)
        
        command_urls = []
        for title, url in links:
            # Filter for YAML/YML files
            if url.endswith(('.yaml', '.yml')) or '/llms.txt' in url:
                command_urls.append(url)
                logger.debug(f"Found automation command URL: {url}")
        
        return command_urls
    
    def _slugify(self, text: str) -> str:
        """Convert text to slug format (lowercase, hyphens)
        
        Args:
            text: Human-readable text
            
        Returns:
            Slugified text suitable for action names
        """
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')


# Utility functions for external use

def discover_and_parse(
    url: str,
    https_only: bool = True,
    cache_ttl: int = 3600
) -> Tuple[DiscoveryResult, Optional[ParsedSections]]:
    """High-level utility to discover and parse llms.txt in one step
    
    Args:
        url: Base URL to discover llms.txt from
        https_only: Enforce HTTPS URLs only
        cache_ttl: Cache time-to-live in seconds
        
    Returns:
        Tuple of (DiscoveryResult, ParsedSections or None)
    """
    source = LlmsTxtSource(url, https_only=https_only, cache_ttl=cache_ttl)
    
    # Auto-discover
    discovery = source.auto_discover()
    if not discovery.success:
        return discovery, None
    
    # Extract sections
    try:
        sections = source.extract_2bykilt_sections()
        return discovery, sections
    except Exception as e:
        logger.error(f"Failed to parse sections: {e}")
        return discovery, None


def validate_discovered_actions(sections: ParsedSections) -> Dict[str, Any]:
    """Validate all discovered actions and return summary
    
    Args:
        sections: ParsedSections to validate
        
    Returns:
        Validation summary with counts and errors
    """
    summary = {
        'total_browser_control': len(sections.browser_control),
        'total_git_scripts': len(sections.git_scripts),
        'total_command_urls': len(sections.command_urls),
        'valid_actions': 0,
        'errors': []
    }
    
    # Validate browser-control actions
    if sections.browser_control:
        try:
            validated = validate_llms_actions(
                {'actions': sections.browser_control},
                strict=False
            )
            summary['valid_actions'] += len(validated)
        except LLMSSchemaValidationError as e:
            summary['errors'].append(f"Browser control validation: {e}")
    
    # Git scripts are already validated by format (just count)
    summary['valid_actions'] += len(sections.git_scripts)
    
    return summary
