"""
Custom Exception Classes for Better Error Handling
"""

from typing import Optional, List


class ValheimModManagerError(Exception):
    """Base exception for all application errors"""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


# Network Errors
class NetworkError(ValheimModManagerError):
    """Base class for network-related errors"""
    pass


class DownloadError(NetworkError):
    """Error during file download"""
    pass


class APIError(NetworkError):
    """Error from Thunderstore API"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[str] = None):
        super().__init__(message, {"status_code": status_code, "response": response})
        self.status_code = status_code
        self.response = response


class TimeoutError(NetworkError):
    """Request timeout error"""
    pass


# File System Errors
class FileSystemError(ValheimModManagerError):
    """Base class for file system errors"""
    pass


class FileNotFoundError(FileSystemError):
    """File not found error"""
    pass


class FileCorruptedError(FileSystemError):
    """File is corrupted"""
    pass


class ExtractionError(FileSystemError):
    """Archive extraction failed"""
    pass


class PermissionError(FileSystemError):
    """Insufficient permissions"""
    pass


# Database Errors
class DatabaseError(ValheimModManagerError):
    """Base class for database errors"""
    pass


class DatabaseConnectionError(DatabaseError):
    """Database connection failed"""
    pass


class DatabaseQueryError(DatabaseError):
    """Database query failed"""
    pass


# Validation Errors
class ValidationError(ValheimModManagerError):
    """Base class for validation errors"""
    pass


class InvalidModIDError(ValidationError):
    """Invalid mod ID format"""
    pass


class InvalidProfileNameError(ValidationError):
    """Invalid profile name"""
    pass


class InvalidConfigValueError(ValidationError):
    """Invalid configuration value"""
    
    def __init__(self, key: str, value: any, expected_type: type):
        super().__init__(
            f"Invalid value for '{key}': got {value} ({type(value).__name__}), expected {expected_type.__name__}",
            {"key": key, "value": value, "expected_type": expected_type}
        )


# Mod Management Errors
class ModError(ValheimModManagerError):
    """Base class for mod-related errors"""
    pass


class ModNotFoundError(ModError):
    """Mod not found"""
    pass


class ModAlreadyExistsError(ModError):
    """Mod already exists"""
    pass


class ModInstallError(ModError):
    """Mod installation failed"""
    pass


class ModUpdateError(ModError):
    """Mod update failed"""
    pass


# Dependency Errors
class DependencyError(ValheimModManagerError):
    """Base class for dependency errors"""
    pass


class CircularDependencyError(DependencyError):
    """Circular dependency detected"""
    
    def __init__(self, dependency_chain: List[str]):
        chain_str = " -> ".join(dependency_chain)
        super().__init__(
            f"Circular dependency detected: {chain_str}",
            {"chain": dependency_chain}
        )
        self.dependency_chain = dependency_chain


class MissingDependencyError(DependencyError):
    """Required dependency is missing"""
    
    def __init__(self, mod_id: str, dependency: str, version: Optional[str] = None):
        version_str = f" (version {version})" if version else ""
        super().__init__(
            f"Mod '{mod_id}' requires '{dependency}'{version_str}",
            {"mod_id": mod_id, "dependency": dependency, "version": version}
        )


class VersionConflictError(DependencyError):
    """Version conflict between dependencies"""
    
    def __init__(self, mod_id: str, required_version: str, actual_version: str):
        super().__init__(
            f"Version conflict for '{mod_id}': requires {required_version}, but {actual_version} is installed",
            {"mod_id": mod_id, "required": required_version, "actual": actual_version}
        )


# Deployment Errors
class DeploymentError(ValheimModManagerError):
    """Base class for deployment errors"""
    pass


class DeploymentFailedError(DeploymentError):
    """Deployment operation failed"""
    pass


class RollbackError(DeploymentError):
    """Rollback operation failed"""
    pass


class GamePathInvalidError(DeploymentError):
    """Game path is invalid"""
    pass


class BepInExNotFoundError(DeploymentError):
    """BepInEx not found in game directory"""
    pass


# Profile Errors
class ProfileError(ValheimModManagerError):
    """Base class for profile errors"""
    pass


class ProfileNotFoundError(ProfileError):
    """Profile not found"""
    pass


class ProfileAlreadyExistsError(ProfileError):
    """Profile already exists"""
    pass


class ProfileInUseError(ProfileError):
    """Profile is currently in use"""
    pass


# Conflict Errors
class ConflictError(ValheimModManagerError):
    """Base class for conflict errors"""
    pass


class FileConflictError(ConflictError):
    """File conflict between mods"""
    
    def __init__(self, file_path: str, conflicting_mods: List[str]):
        mods_str = ", ".join(conflicting_mods)
        super().__init__(
            f"File conflict: '{file_path}' is modified by multiple mods: {mods_str}",
            {"file_path": file_path, "mods": conflicting_mods}
        )


# Backup Errors
class BackupError(ValheimModManagerError):
    """Base class for backup errors"""
    pass


class BackupNotFoundError(BackupError):
    """Backup not found"""
    pass


class BackupRestoreError(BackupError):
    """Backup restore failed"""
    pass


# Configuration Errors
class ConfigError(ValheimModManagerError):
    """Base class for configuration errors"""
    pass


class ConfigNotFoundError(ConfigError):
    """Configuration file not found"""
    pass


class ConfigParseError(ConfigError):
    """Configuration file parse error"""
    pass


class ConfigValidationError(ConfigError):
    """Configuration validation failed"""
    
    def __init__(self, errors: List[str]):
        super().__init__(
            f"Configuration validation failed: {len(errors)} error(s)",
            {"errors": errors}
        )
        self.errors = errors


# Recovery decorators
def with_rollback(func):
    """Decorator to automatically rollback on error"""
    def wrapper(self, *args, **kwargs):
        checkpoint = None
        if hasattr(self, 'create_checkpoint'):
            checkpoint = self.create_checkpoint()
        
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            if checkpoint and hasattr(self, 'rollback'):
                try:
                    self.rollback(checkpoint)
                except Exception as rollback_error:
                    raise RollbackError(f"Rollback failed: {rollback_error}") from e
            raise
    return wrapper


def retry_on_network_error(max_retries: int = 3):
    """Decorator to retry on network errors"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except NetworkError as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        continue
            raise last_error
        return wrapper
    return decorator
