import asyncio
import json
from typing import Any, Dict, Optional

class AgentState:
    _instance = None

    def __init__(self):
        if not hasattr(self, '_stop_requested'):
            self._stop_requested = asyncio.Event()
            self.last_valid_state = None  # store the last valid browser state
            # Add data storage for extracted content
            self._extracted_data = {}
            self._data_history = []  # To maintain history of extracted data

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentState, cls).__new__(cls)
        return cls._instance

    def request_stop(self):
        self._stop_requested.set()

    def clear_stop(self):
        self._stop_requested.clear()
        self.last_valid_state = None

    def is_stop_requested(self):
        return self._stop_requested.is_set()

    def set_last_valid_state(self, state):
        self.last_valid_state = state

    def get_last_valid_state(self):
        return self.last_valid_state
        
    # Data storage methods
    def store_extracted_data(self, key: str, data: Any, source: Optional[str] = None) -> None:
        """
        Store extracted data with a key for later use
        
        Args:
            key: Identifier for the data
            data: The extracted data to store
            source: Optional source information (e.g., URL or selector)
        """
        self._extracted_data[key] = data
        # Store in history with timestamp
        import datetime
        history_entry = {
            'key': key,
            'data': data,
            'source': source,
            'timestamp': datetime.datetime.now().isoformat()
        }
        self._data_history.append(history_entry)
    
    def get_extracted_data(self, key: str, default: Any = None) -> Any:
        """
        Retrieve previously extracted data
        
        Args:
            key: Identifier for the data
            default: Value to return if key doesn't exist
            
        Returns:
            The stored data or default value
        """
        return self._extracted_data.get(key, default)
    
    def get_all_extracted_data(self) -> Dict[str, Any]:
        """
        Get all extracted data
        
        Returns:
            Dictionary of all stored data
        """
        return self._extracted_data
        
    def get_data_history(self):
        """
        Get history of all extracted data with timestamps
        
        Returns:
            List of history entries
        """
        return self._data_history
        
    def clear_extracted_data(self):
        """Clear all stored data"""
        self._extracted_data = {}
        
    def export_data_as_json(self) -> str:
        """
        Export all extracted data as JSON string
        
        Returns:
            JSON string representation of extracted data
        """
        return json.dumps(self._extracted_data, indent=2, ensure_ascii=False)