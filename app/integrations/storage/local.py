"""
Local Storage Implementation
For development and testing purposes
"""
import os
import shutil
from typing import Optional, BinaryIO
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalStorage:
    """Local file system storage for development"""
    
    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    async def upload_file(
        self, 
        file_obj: BinaryIO, 
        object_key: str,
        content_type: Optional[str] = None
    ) -> bool:
        """
        Save file to local storage
        
        Args:
            file_obj: File object to save
            object_key: File path relative to base_path
            content_type: MIME type (ignored for local storage)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_path = self.base_path / object_key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_obj, f)
            
            logger.info(f"File saved locally: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving file locally: {e}")
            return False
    
    async def delete_file(self, object_key: str) -> bool:
        """
        Delete file from local storage
        
        Args:
            object_key: File path relative to base_path
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_path = self.base_path / object_key
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    async def get_file_path(self, object_key: str) -> Optional[str]:
        """
        Get local file path
        
        Args:
            object_key: File path relative to base_path
            
        Returns:
            str: Absolute file path or None if not found
        """
        file_path = self.base_path / object_key
        return str(file_path) if file_path.exists() else None


# Global local storage instance
local_storage = LocalStorage()
