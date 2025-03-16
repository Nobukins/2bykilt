import re
import requests
import yaml
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class InstructionResult:
    """Container for instruction loading results with source tracking and error information"""
    success: bool
    instructions: List[Dict[str, Any]]
    source: str
    error: Optional[str] = None

@dataclass
class YamlInstructionSource:
    url: str
    raw_content: Optional[str] = None
    
    def fetch(self) -> str:
        """Fetch content from the URL."""
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            self.raw_content = response.text
            return self.raw_content
        except requests.RequestException as e:
            logger.error(f"Failed to fetch content from {self.url}: {e}")
            raise

class MarkdownYamlParser:
    def __init__(self, markdown_content: str):
        self.markdown_content = markdown_content
    
    def extract_yaml_blocks(self) -> List[str]:
        """Extract YAML code blocks from Markdown content."""
        # Pattern to match code blocks with yaml language identifier
        pattern = r'```yaml\s+(.*?)\s+```'
        # re.DOTALL makes '.' match newlines as well
        matches = re.findall(pattern, self.markdown_content, re.DOTALL)
        
        if not matches:
            logger.warning("No YAML code blocks found in the Markdown content")
        
        return matches
    
    def parse_yaml_blocks(self) -> List[Dict[str, Any]]:
        """Extract and parse YAML blocks from Markdown content."""
        yaml_blocks = self.extract_yaml_blocks()
        parsed_blocks = []
        
        for i, block in enumerate(yaml_blocks):
            try:
                # Use safe_load to prevent execution of arbitrary code
                parsed_yaml = yaml.safe_load(block)
                if isinstance(parsed_yaml, list):
                    parsed_blocks.extend(parsed_yaml)
                else:
                    parsed_blocks.append(parsed_yaml)
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML block {i+1}: {e}")
        
        return parsed_blocks

class BrowserAutomationConfig:
    def __init__(self, config_url: str):
        self.config_url = config_url
        self.yaml_instructions = []
    
    def load_from_remote(self) -> List[Dict[str, Any]]:
        """Load browser automation instructions from a remote URL."""
        source = YamlInstructionSource(self.config_url)
        markdown_content = source.fetch()
        
        parser = MarkdownYamlParser(markdown_content)
        self.yaml_instructions = parser.parse_yaml_blocks()
        
        return self.yaml_instructions
    
    def validate_instruction(self, instruction: Dict[str, Any]) -> bool:
        """Validate a single browser automation instruction."""
        required_fields = ['name', 'type']
        
        # Check required fields
        for field in required_fields:
            if field not in instruction:
                logger.error(f"Missing required field '{field}' in instruction")
                return False
        
        # Validate type-specific requirements
        if instruction['type'] == 'browser-control':
            if 'params' not in instruction:
                logger.error(f"Missing 'params' field in browser-control instruction")
                return False
            if 'flow' not in instruction:
                logger.error(f"Missing 'flow' field in browser-control instruction")
                return False
        
        return True
    
    def get_valid_instructions(self) -> List[Dict[str, Any]]:
        """Get only the valid browser automation instructions."""
        return [instr for instr in self.yaml_instructions if self.validate_instruction(instr)]

class InstructionLoader:
    """Handles loading browser automation instructions from different sources"""
    
    def __init__(self, local_path: str = "llms.txt", website_url: Optional[str] = None):
        self.local_path = local_path
        self.website_url = website_url
    
    def load_instructions(self) -> InstructionResult:
        """
        Load instructions following priority order:
        1. Local file
        2. Website
        3. Fallback to LLM (by returning empty result)
        """
        logger.info("Attempting to load instructions from available sources")
        
        # Priority 1: Try local file first (user's content takes precedence)
        local_result = self._load_from_local()
        if local_result.success:
            logger.info("Successfully loaded instructions from local file")
            return local_result
        
        # Priority 2: If local file not available or invalid, try website
        if self.website_url:
            website_result = self._load_from_website()
            if website_result.success:
                logger.info("Successfully loaded instructions from website")
                return website_result
        
        # Priority 3: Both failed, indicate failure (will trigger LLM fallback)
        logger.warning("Failed to load instructions from all sources")
        return InstructionResult(
            success=False,
            instructions=[],
            source="none",
            error="Failed to load instructions from both local file and website"
        )
    
    def _load_from_local(self) -> InstructionResult:
        """Attempt to load instructions from local file with error handling"""
        try:
            if not os.path.exists(self.local_path):
                logger.warning(f"Local file not found: {self.local_path}")
                return InstructionResult(
                    success=False, 
                    instructions=[], 
                    source="local",
                    error=f"Local file not found: {self.local_path}"
                )
            
            logger.info(f"Reading local file: {self.local_path}")
            with open(self.local_path, 'r') as file:
                content = file.read()
            
            instructions = self._parse_content(content)
            if not instructions:
                return InstructionResult(
                    success=False, 
                    instructions=[], 
                    source="local",
                    error="No valid instructions found in local file"
                )
            
            return InstructionResult(success=True, instructions=instructions, source="local")
        except Exception as e:
            logger.error(f"Error loading from local file: {str(e)}")
            return InstructionResult(
                success=False, 
                instructions=[], 
                source="local",
                error=f"Error processing local file: {str(e)}"
            )
    
    def _load_from_website(self) -> InstructionResult:
        """Attempt to load instructions from website with error handling"""
        try:
            # Construct URL for llms.txt
            url = self.website_url
            if not url.endswith('/llms.txt'):
                if not url.endswith('/'):
                    url += '/'
                url += 'llms.txt'
            
            logger.info(f"Fetching instructions from: {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Website returned status {response.status_code}")
                return InstructionResult(
                    success=False, 
                    instructions=[], 
                    source="website",
                    error=f"Website returned status code: {response.status_code}"
                )
            
            instructions = self._parse_content(response.text)
            if not instructions:
                return InstructionResult(
                    success=False, 
                    instructions=[], 
                    source="website",
                    error="No valid instructions found in website content"
                )
            
            return InstructionResult(success=True, instructions=instructions, source="website")
        except requests.RequestException as e:
            logger.error(f"Network error fetching from website: {str(e)}")
            return InstructionResult(
                success=False, 
                instructions=[], 
                source="website",
                error=f"Network error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error processing website content: {str(e)}")
            return InstructionResult(
                success=False, 
                instructions=[], 
                source="website",
                error=f"Error: {str(e)}"
            )
    
    def _parse_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse content to extract YAML instructions from Markdown blocks"""
        try:
            # Extract YAML blocks from Markdown
            yaml_pattern = r'```\s*yaml\s*([\s\S]*?)```'
            matches = re.findall(yaml_pattern, content)
            
            if not matches:
                logger.warning("No YAML code blocks found in content")
                # Try parsing the entire content as YAML as fallback
                try:
                    parsed = yaml.safe_load(content)
                    if isinstance(parsed, dict) and 'actions' in parsed:
                        return parsed['actions']
                    elif isinstance(parsed, list):
                        return parsed
                    return []
                except yaml.YAMLError:
                    return []
            
            # Process each YAML block
            all_instructions = []
            for i, block in enumerate(matches):
                try:
                    cleaned_block = block.strip()
                    parsed = yaml.safe_load(cleaned_block)
                    
                    if isinstance(parsed, list):
                        all_instructions.extend(parsed)
                    elif isinstance(parsed, dict):
                        if 'actions' in parsed:
                            all_instructions.extend(parsed['actions'])
                        else:
                            all_instructions.append(parsed)
                except yaml.YAMLError as e:
                    logger.error(f"Error parsing YAML block {i+1}: {e}")
            
            # Validate instructions
            return [
                action for action in all_instructions 
                if isinstance(action, dict) and 'name' in action
            ]
        except Exception as e:
            logger.error(f"Error parsing content: {e}")
            return []