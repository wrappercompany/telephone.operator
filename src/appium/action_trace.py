from __future__ import annotations

import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class ActionTracer:
    """
    Records all actions performed by the Appium driver into a JSON trace file.
    """
    def __init__(self):
        self.actions: List[Dict[str, Any]] = []
        self.active_trace_path: Optional[str] = None
        self.app_dir_name: Optional[str] = None
        self.bundle_id: Optional[str] = None
        self.session_start_time = datetime.now()
        self.network_requests: List[Dict[str, Any]] = []
        self.current_app_state: Dict[str, Any] = {
            "current_activity": None,
            "current_screen": None,
            "current_view": None,
            "last_page_source_hash": None
        }
        
    def start_new_trace(self, app_dir_name: str, bundle_id: Optional[str] = None) -> None:
        """
        Start a new trace session for an app.
        
        Args:
            app_dir_name: Directory name for the app
            bundle_id: Bundle ID if available
        """
        self.actions = []
        self.app_dir_name = app_dir_name
        self.bundle_id = bundle_id
        self.session_start_time = datetime.now()
        self.network_requests = []
        self.current_app_state = {
            "current_activity": None,
            "current_screen": None,
            "current_view": None,
            "last_page_source_hash": None
        }
        
        # Create trace directory if it doesn't exist
        self._ensure_trace_dir()
        
        # Generate a new trace file path
        timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S")
        self.active_trace_path = str(Path("artifacts") / app_dir_name / "traces" / f"action_trace_{timestamp}.json")
        
        # Log the initial session info
        self.log_action(
            action_type="session_start",
            details={
                "app": app_dir_name,
                "bundle_id": bundle_id,
                "timestamp": timestamp
            }
        )
        
        logger.info(f"Started new action trace at {self.active_trace_path}")
    
    def _ensure_trace_dir(self) -> None:
        """Ensure the trace directory exists."""
        if not self.app_dir_name:
            logger.warning("Cannot create trace directory: No app directory name set")
            return
            
        trace_dir = Path("artifacts") / self.app_dir_name / "traces"
        try:
            trace_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured trace directory exists: {trace_dir}")
        except Exception as e:
            logger.error(f"Failed to create trace directory {trace_dir}: {str(e)}")
    
    def update_app_state(self, **kwargs) -> None:
        """
        Update the current app state information.
        
        Args:
            **kwargs: Any key-value pairs to update in the current_app_state dict
        """
        for key, value in kwargs.items():
            if key in self.current_app_state:
                self.current_app_state[key] = value
    
    def log_network_request(self, url: str, method: str, status: Optional[int] = None, 
                          request_data: Optional[Dict[str, Any]] = None,
                          response_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a network request to the trace.
        
        Args:
            url: The URL of the request
            method: HTTP method (GET, POST, etc.)
            status: HTTP status code if available
            request_data: Request data if available
            response_data: Response data if available
        """
        if not self.active_trace_path:
            logger.warning("Cannot log network request: No active trace")
            return
            
        network_event = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "method": method,
            "status": status
        }
        
        if request_data:
            network_event["request_data"] = request_data
            
        if response_data:
            network_event["response_data"] = response_data
            
        self.network_requests.append(network_event)
        logger.debug(f"Logged network request: {url}")
        
        # Write to file with updated network requests
        self._write_trace_to_file()
    
    def log_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """
        Log an action to the trace.
        
        Args:
            action_type: Type of action (e.g., tap, swipe, screenshot)
            details: Details about the action
        """
        if not self.active_trace_path:
            logger.warning("Cannot log action: No active trace")
            return
            
        # Add current app state information to the action details
        app_state_copy = self.current_app_state.copy()
        
        # Create the action entry
        action_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "details": details,
            "app_state": app_state_copy,
            "timestamp_millis": int(time.time() * 1000)  # Add millisecond timestamp for ordering
        }
        
        # Add to in-memory list
        self.actions.append(action_entry)
        
        # Write to file
        self._write_trace_to_file()
        logger.debug(f"Logged action: {action_type}")
    
    def _write_trace_to_file(self) -> None:
        """Write the current trace data to file."""
        try:
            # Create parent directory if it doesn't exist
            trace_file = Path(self.active_trace_path)
            trace_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write all actions to file
            with open(self.active_trace_path, 'w') as f:
                json.dump({
                    "app": self.app_dir_name,
                    "bundle_id": self.bundle_id,
                    "session_start": self.session_start_time.isoformat(),
                    "actions": self.actions,
                    "network_requests": self.network_requests
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write action trace: {str(e)}")
    
    def end_trace(self) -> None:
        """End the current trace session."""
        if not self.active_trace_path:
            logger.warning("Cannot end trace: No active trace")
            return
            
        # Log the session end
        self.log_action(
            action_type="session_end",
            details={
                "app": self.app_dir_name,
                "bundle_id": self.bundle_id,
                "duration_seconds": (datetime.now() - self.session_start_time).total_seconds()
            }
        )
        
        logger.info(f"Ended action trace at {self.active_trace_path}")
        self.active_trace_path = None

# Create singleton instance
action_tracer = ActionTracer() 