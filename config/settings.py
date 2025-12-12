"""
Application Settings and Constants
"""

from pathlib import Path
from typing import Final
import platform


class Settings:
    """Global application settings"""
    
    # Version
    VERSION: Final[str] = "1.0.0"
    APP_NAME: Final[str] = "Valheim Mod Manager"
    
    # Paths
    PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent
    DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
    MODS_DIR: Final[Path] = DATA_DIR / "mods"
    PROFILES_DIR: Final[Path] = DATA_DIR / "profiles"
    CONFIGS_DIR: Final[Path] = DATA_DIR / "configs"
    CACHE_DIR: Final[Path] = DATA_DIR / "cache"
    LOGS_DIR: Final[Path] = DATA_DIR / "logs"
    BACKUPS_DIR: Final[Path] = DATA_DIR / "backups"
    TEMP_DIR: Final[Path] = DATA_DIR / "temp"
    
    RESOURCES_DIR: Final[Path] = PROJECT_ROOT / "resources"
    DATABASE_PATH: Final[Path] = DATA_DIR / "valheim_mods.db"
    
    # Thunderstore API
    THUNDERSTORE_API_BASE: Final[str] = "https://thunderstore.io/api/experimental"
    THUNDERSTORE_COMMUNITY: Final[str] = "valheim"
    THUNDERSTORE_PACKAGES_URL: Final[str] = (
        f"{THUNDERSTORE_API_BASE}/community/{THUNDERSTORE_COMMUNITY}/package/"
    )
    
    # Network Settings
    REQUEST_TIMEOUT: Final[int] = 30
    MAX_RETRIES: Final[int] = 3
    RETRY_BACKOFF: Final[float] = 1.0
    CACHE_DURATION_HOURS: Final[int] = 6
    CHUNK_SIZE: Final[int] = 8192
    MAX_CONCURRENT_DOWNLOADS: Final[int] = 3
    
    # UI Settings
    WINDOW_WIDTH: Final[int] = 1280
    WINDOW_HEIGHT: Final[int] = 800
    ICON_SIZE_SMALL: Final[int] = 32
    ICON_SIZE_MEDIUM: Final[int] = 64
    ICON_SIZE_LARGE: Final[int] = 128
    MAX_ICON_CACHE_SIZE: Final[int] = 100
    
    # Performance Settings
    MAX_SEARCH_RESULTS: Final[int] = 1000
    PAGE_SIZE: Final[int] = 50
    LAZY_LOAD_THRESHOLD: Final[int] = 100
    
    # Hash Settings
    HASH_ALGORITHM: Final[str] = "xxhash64"
    
    # Backup Settings
    MAX_BACKUPS_PER_PROFILE: Final[int] = 5
    AUTO_BACKUP_BEFORE_DEPLOY: Final[bool] = True
    
    # Logging Settings
    LOG_LEVEL: Final[str] = "INFO"
    LOG_MAX_BYTES: Final[int] = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: Final[int] = 5
    
    # Game Detection
    DEFAULT_GAME_PATHS = {
        "Windows": [
            Path("C:/Program Files (x86)/Steam/steamapps/common/Valheim"),
            Path("C:/Program Files/Steam/steamapps/common/Valheim"),
        ],
        "Linux": [
            Path.home() / ".steam/steam/steamapps/common/Valheim",
            Path.home() / ".local/share/Steam/steamapps/common/Valheim",
        ],
        "Darwin": [  # macOS
            Path.home() / "Library/Application Support/Steam/steamapps/common/Valheim",
        ],
    }
    
    @classmethod
    def get_default_game_paths(cls):
        """Get default game paths for current OS"""
        system = platform.system()
        return cls.DEFAULT_GAME_PATHS.get(system, [])
    
    # BepInEx Paths
    BEPINEX_CORE_FILES = [
        "BepInEx/core/BepInEx.dll",
        "BepInEx/core/0Harmony.dll",
        "BepInEx/core/Mono.Cecil.dll",
    ]
    
    BEPINEX_PLUGINS_DIR = "BepInEx/plugins"
    BEPINEX_CONFIG_DIR = "BepInEx/config"
    
    # File Extensions
    MOD_ARCHIVE_EXTENSIONS = [".zip"]
    CONFIG_EXTENSIONS = [".cfg", ".json", ".yaml", ".yml"]
    DOCUMENTATION_EXTENSIONS = [".md", ".txt"]
    
    # Validation Rules
    MIN_PROFILE_NAME_LENGTH: Final[int] = 1
    MAX_PROFILE_NAME_LENGTH: Final[int] = 50
    INVALID_PROFILE_CHARS: Final[str] = r'<>:"/\|?*'
    
    # Feature Flags
    ENABLE_ANALYTICS: Final[bool] = False  # Opt-in only
    ENABLE_AUTO_UPDATE: Final[bool] = True
    ENABLE_CONFLICT_DETECTION: Final[bool] = True
    ENABLE_DEPENDENCY_AUTO_RESOLVE: Final[bool] = True
    
    # Analytics (if enabled)
    ANALYTICS_ENDPOINT: Final[str] = "https://analytics.example.com/track"
    
    # Update Checker
    UPDATE_CHECK_URL: Final[str] = (
        "https://api.github.com/repos/yourusername/valheim-mod-manager/releases/latest"
    )
    UPDATE_CHECK_INTERVAL_HOURS: Final[int] = 24


class ConfigValidationRules:
    """Configuration file validation rules"""
    
    VALHEIM_PLUS_RULES = {
        "Server": {
            "enabled": {"type": bool, "default": True},
            "enforceMod": {"type": bool, "default": True},
            "maxPlayers": {"type": int, "min": 1, "max": 10, "default": 10},
            "serverPassword": {"type": str, "max_length": 256, "default": ""},
        },
        "Building": {
            "enabled": {"type": bool, "default": True},
            "noInvalidPlacementRestriction": {"type": bool, "default": False},
            "noWeatherDamage": {"type": bool, "default": False},
            "maximumPlacementDistance": {"type": float, "min": 1.0, "max": 50.0, "default": 8.0},
        },
        "Player": {
            "enabled": {"type": bool, "default": True},
            "baseMaximumWeight": {"type": float, "min": 0.0, "max": 10000.0, "default": 300.0},
            "baseMegingjordBuff": {"type": float, "min": 0.0, "max": 10000.0, "default": 150.0},
            "baseAutoPickUpRange": {"type": float, "min": 0.0, "max": 50.0, "default": 2.0},
        },
    }
    
    @classmethod
    def get_rules(cls, config_name: str) -> dict:
        """Get validation rules for specific config file"""
        if "valheim_plus" in config_name.lower():
            return cls.VALHEIM_PLUS_RULES
        return {}


class ErrorMessages:
    """Centralized error messages"""
    
    # Network Errors
    NETWORK_ERROR = "Network error: {error}"
    DOWNLOAD_FAILED = "Failed to download {item}: {error}"
    API_ERROR = "API request failed: {error}"
    TIMEOUT_ERROR = "Request timed out after {seconds} seconds"
    
    # File Errors
    FILE_NOT_FOUND = "File not found: {path}"
    FILE_CORRUPTED = "File is corrupted: {path}"
    EXTRACTION_FAILED = "Failed to extract archive: {error}"
    PERMISSION_DENIED = "Permission denied: {path}"
    
    # Database Errors
    DB_CONNECTION_ERROR = "Database connection failed: {error}"
    DB_QUERY_ERROR = "Database query failed: {error}"
    
    # Validation Errors
    INVALID_MOD_ID = "Invalid mod ID format: {mod_id}"
    INVALID_PROFILE_NAME = "Invalid profile name: {name}"
    INVALID_CONFIG_VALUE = "Invalid config value for {key}: {value}"
    
    # Deployment Errors
    DEPLOYMENT_FAILED = "Deployment failed: {error}"
    ROLLBACK_FAILED = "Rollback failed: {error}"
    GAME_PATH_INVALID = "Game path is invalid: {path}"
    
    # Dependency Errors
    CIRCULAR_DEPENDENCY = "Circular dependency detected: {chain}"
    MISSING_DEPENDENCY = "Missing dependency: {mod_id} requires {dependency}"
    VERSION_CONFLICT = "Version conflict: {details}"


class SuccessMessages:
    """Centralized success messages"""
    
    MOD_DOWNLOADED = "Mod '{name}' downloaded successfully"
    MOD_UPDATED = "Mod '{name}' updated to version {version}"
    PROFILE_CREATED = "Profile '{name}' created"
    PROFILE_DEPLOYED = "Profile '{name}' deployed successfully"
    CONFIG_SAVED = "Configuration saved"
    BACKUP_CREATED = "Backup created: {name}"
    BACKUP_RESTORED = "Backup restored successfully"
