"""
Input Validation Utilities
"""

import re
from pathlib import Path
from typing import Tuple, Optional

from config.settings import Settings
from core.exceptions import (
    ValidationError,
    InvalidModIDError,
    InvalidProfileNameError
)


def validate_mod_id(mod_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate mod ID format
    
    Format: Author-ModName
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not mod_id:
        return False, "Mod ID cannot be empty"
    
    if not isinstance(mod_id, str):
        return False, "Mod ID must be a string"
    
    # Check format
    pattern = r'^[a-zA-Z0-9_]+-[a-zA-Z0-9_]+$'
    if not re.match(pattern, mod_id):
        return False, "Mod ID must be in format: Author-ModName"
    
    # Check length
    if len(mod_id) > 100:
        return False, "Mod ID is too long (max 100 characters)"
    
    return True, None


def validate_profile_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate profile name
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Profile name cannot be empty"
    
    if not isinstance(name, str):
        return False, "Profile name must be a string"
    
    # Check length
    if len(name) < Settings.MIN_PROFILE_NAME_LENGTH:
        return False, f"Profile name too short (min {Settings.MIN_PROFILE_NAME_LENGTH} chars)"
    
    if len(name) > Settings.MAX_PROFILE_NAME_LENGTH:
        return False, f"Profile name too long (max {Settings.MAX_PROFILE_NAME_LENGTH} chars)"
    
    # Check for invalid characters
    invalid_chars = Settings.INVALID_PROFILE_CHARS
    for char in invalid_chars:
        if char in name:
            return False, f"Profile name contains invalid character: '{char}'"
    
    return True, None


def validate_version(version: str) -> Tuple[bool, Optional[str]]:
    """
    Validate semantic version string
    
    Format: MAJOR.MINOR.PATCH
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not version:
        return False, "Version cannot be empty"
    
    # Check semantic version format
    pattern = r'^\d+\.\d+\.\d+$'
    if not re.match(pattern, version):
        return False, "Version must be in format: MAJOR.MINOR.PATCH (e.g., 1.2.3)"
    
    return True, None


def validate_game_path(path: Path) -> Tuple[bool, Optional[str]]:
    """
    Validate game installation path
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "Game path cannot be empty"
    
    if not isinstance(path, Path):
        try:
            path = Path(path)
        except Exception:
            return False, "Invalid path format"
    
    # Check if path exists
    if not path.exists():
        return False, f"Path does not exist: {path}"
    
    # Check if directory
    if not path.is_dir():
        return False, f"Path is not a directory: {path}"
    
    # Check for Valheim executable
    exe_names = ['valheim.exe', 'valheim', 'valheim.x86_64']
    has_exe = any((path / exe).exists() for exe in exe_names)
    
    if not has_exe:
        return False, f"Valheim executable not found in: {path}"
    
    return True, None


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"
    
    # Simple URL validation
    pattern = r'^https?://[\w\-\.]+\.[a-z]{2,}(/.*)?$'
    if not re.match(pattern, url, re.IGNORECASE):
        return False, "Invalid URL format"
    
    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email cannot be empty"
    
    # Basic email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, None


def validate_file_path(path: Path, must_exist: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate file path
    
    Args:
        path: Path to validate
        must_exist: If True, file must exist
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "File path cannot be empty"
    
    if not isinstance(path, Path):
        try:
            path = Path(path)
        except Exception:
            return False, "Invalid path format"
    
    if must_exist and not path.exists():
        return False, f"File does not exist: {path}"
    
    if must_exist and not path.is_file():
        return False, f"Path is not a file: {path}"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    # Remove invalid filesystem characters
    invalid_chars = r'<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing whitespace and dots
    filename = filename.strip(' .')
    
    # Ensure not empty
    if not filename:
        filename = 'unnamed'
    
    return filename


def sanitize_profile_name(name: str) -> str:
    """
    Sanitize profile name
    
    Args:
        name: Original profile name
    
    Returns:
        Sanitized profile name
    """
    return sanitize_filename(name)


def validate_port(port: int) -> Tuple[bool, Optional[str]]:
    """
    Validate network port number
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(port, int):
        return False, "Port must be an integer"
    
    if port < 1 or port > 65535:
        return False, "Port must be between 1 and 65535"
    
    return True, None


def validate_positive_integer(value: int, min_value: int = 1) -> Tuple[bool, Optional[str]]:
    """
    Validate positive integer
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(value, int):
        return False, "Value must be an integer"
    
    if value < min_value:
        return False, f"Value must be at least {min_value}"
    
    return True, None


def validate_in_range(
    value: float,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate numeric value is within range
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(value, (int, float)):
        return False, "Value must be numeric"
    
    if min_value is not None and value < min_value:
        return False, f"Value must be at least {min_value}"
    
    if max_value is not None and value > max_value:
        return False, f"Value must be at most {max_value}"
    
    return True, None


def validate_choice(value: str, choices: list) -> Tuple[bool, Optional[str]]:
    """
    Validate value is in allowed choices
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if value not in choices:
        return False, f"Value must be one of: {', '.join(choices)}"
    
    return True, None


def validate_regex(value: str, pattern: str, message: str = None) -> Tuple[bool, Optional[str]]:
    """
    Validate value matches regex pattern
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not re.match(pattern, value):
        return False, message or f"Value does not match required pattern"
    
    return True, None


class Validator:
    """Validator class for chaining validations"""
    
    def __init__(self, value):
        self.value = value
        self.errors = []
    
    def required(self, message: str = "Value is required"):
        """Check value is not empty"""
        if not self.value:
            self.errors.append(message)
        return self
    
    def min_length(self, length: int, message: str = None):
        """Check minimum length"""
        if len(str(self.value)) < length:
            self.errors.append(
                message or f"Minimum length is {length}"
            )
        return self
    
    def max_length(self, length: int, message: str = None):
        """Check maximum length"""
        if len(str(self.value)) > length:
            self.errors.append(
                message or f"Maximum length is {length}"
            )
        return self
    
    def matches(self, pattern: str, message: str = None):
        """Check matches regex pattern"""
        if not re.match(pattern, str(self.value)):
            self.errors.append(
                message or "Value does not match required pattern"
            )
        return self
    
    def is_valid(self) -> bool:
        """Check if all validations passed"""
        return len(self.errors) == 0
    
    def get_errors(self) -> list:
        """Get list of validation errors"""
        return self.errors
    
    def get_error_message(self) -> str:
        """Get concatenated error message"""
        return "; ".join(self.errors)


# Convenience functions that raise exceptions
def assert_valid_mod_id(mod_id: str):
    """Assert mod ID is valid, raise exception if not"""
    valid, error = validate_mod_id(mod_id)
    if not valid:
        raise InvalidModIDError(error)


def assert_valid_profile_name(name: str):
    """Assert profile name is valid, raise exception if not"""
    valid, error = validate_profile_name(name)
    if not valid:
        raise InvalidProfileNameError(error)


def assert_valid_path(path: Path, must_exist: bool = True):
    """Assert path is valid, raise exception if not"""
    valid, error = validate_file_path(path, must_exist)
    if not valid:
        raise ValidationError(error)
