"""
Configuration File Manager with Validation
"""

import configparser
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from core.models import ModConfig
from core.database import Database
from core.exceptions import (
    ConfigError,
    ConfigNotFoundError,
    ConfigParseError,
    ConfigValidationError
)
from config.settings import Settings, ConfigValidationRules
from utils.logger import LoggerMixin


class ConfigManager(LoggerMixin):
    """Manages mod configuration files"""
    
    def __init__(self, database: Database = None):
        self.db = database or Database()
        self.validation_rules = ConfigValidationRules()
    
    def load_config(
        self,
        mod_id: str,
        profile_name: str = "default"
    ) -> Optional[ModConfig]:
        """
        Load configuration for mod in profile
        
        Priority:
        1. Profile-specific custom config
        2. Default mod config
        
        Args:
            mod_id: Mod identifier
            profile_name: Profile name
        
        Returns:
            ModConfig object or None
        """
        # Check for profile-specific config
        profile_config_path = self._get_profile_config_path(mod_id, profile_name)
        
        if profile_config_path.exists():
            self.logger.debug(f"Loading profile config: {profile_config_path}")
            config = ModConfig(
                mod_id=mod_id,
                profile_name=profile_name,
                config_name=profile_config_path.name,
                is_custom=True
            )
            config.load_from_file(profile_config_path)
            return config
        
        # Fall back to default config
        default_config_path = self._get_default_config_path(mod_id)
        
        if default_config_path.exists():
            self.logger.debug(f"Loading default config: {default_config_path}")
            config = ModConfig(
                mod_id=mod_id,
                profile_name=profile_name,
                config_name=default_config_path.name,
                is_custom=False
            )
            config.load_from_file(default_config_path)
            return config
        
        return None
    
    def save_config(self, config: ModConfig) -> bool:
        """
        Save configuration file
        
        Args:
            config: ModConfig object to save
        
        Returns:
            True if successful
        """
        try:
            if config.is_custom:
                # Save to profile-specific location
                save_path = self._get_profile_config_path(
                    config.mod_id,
                    config.profile_name
                )
            else:
                # Save to default location
                save_path = self._get_default_config_path(config.mod_id)
            
            config.save_to_file(save_path)
            self.logger.info(f"Saved config: {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            raise ConfigError(f"Failed to save config: {e}")
    
    def _get_default_config_path(self, mod_id: str) -> Path:
        """Get path to default config file"""
        mod = self.db.get_mod(mod_id)
        if mod and mod.install_path:
            # Look for config files in mod directory
            for config_file in mod.config_files:
                config_path = mod.install_path / "configs" / config_file
                if config_path.exists():
                    return config_path
        
        # Fallback to configs directory
        return Settings.CONFIGS_DIR / "default" / mod_id
    
    def _get_profile_config_path(self, mod_id: str, profile_name: str) -> Path:
        """Get path to profile-specific config file"""
        return Settings.CONFIGS_DIR / profile_name / mod_id
    
    def create_profile_override(
        self,
        mod_id: str,
        profile_name: str,
        config_name: str
    ) -> ModConfig:
        """
        Create profile-specific config override
        
        Copies default config to profile directory for customization
        """
        # Load default config
        default_config = self.load_config(mod_id, "default")
        
        if not default_config:
            raise ConfigNotFoundError(f"No default config found for {mod_id}")
        
        # Create profile override
        profile_config = ModConfig(
            mod_id=mod_id,
            profile_name=profile_name,
            config_name=config_name,
            content=default_config.content,
            is_custom=True
        )
        
        self.save_config(profile_config)
        self.logger.info(f"Created profile override: {mod_id} for {profile_name}")
        
        return profile_config
    
    def reset_to_default(self, mod_id: str, profile_name: str) -> bool:
        """
        Reset profile config to default
        
        Removes profile-specific override
        """
        try:
            profile_config_path = self._get_profile_config_path(mod_id, profile_name)
            
            if profile_config_path.exists():
                profile_config_path.unlink()
                self.logger.info(f"Reset config to default: {mod_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to reset config: {e}")
            return False
    
    def validate_config(self, config: ModConfig) -> Tuple[bool, List[str]]:
        """
        Validate configuration content
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Get validation rules for this config
            rules = self.validation_rules.get_rules(config.config_name)
            
            if not rules:
                # No rules defined, skip validation
                return True, []
            
            # Parse config file
            parser = configparser.ConfigParser()
            parser.read_string(config.content)
            
            # Validate each section and key
            for section, section_rules in rules.items():
                if section not in parser:
                    errors.append(f"Missing section: [{section}]")
                    continue
                
                for key, rule in section_rules.items():
                    if key not in parser[section]:
                        if rule.get('required', False):
                            errors.append(f"Missing required key: {section}.{key}")
                        continue
                    
                    value_str = parser[section][key]
                    
                    # Type validation
                    expected_type = rule.get('type')
                    if expected_type:
                        error = self._validate_type(
                            value_str,
                            expected_type,
                            f"{section}.{key}"
                        )
                        if error:
                            errors.append(error)
                    
                    # Range validation
                    if 'min' in rule or 'max' in rule:
                        error = self._validate_range(
                            value_str,
                            rule.get('min'),
                            rule.get('max'),
                            f"{section}.{key}"
                        )
                        if error:
                            errors.append(error)
            
            return len(errors) == 0, errors
            
        except configparser.Error as e:
            errors.append(f"Config parse error: {e}")
            return False, errors
        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, errors
    
    def _validate_type(
        self,
        value: str,
        expected_type: type,
        key: str
    ) -> Optional[str]:
        """Validate value type"""
        try:
            if expected_type == bool:
                if value.lower() not in ['true', 'false']:
                    return f"{key}: Expected boolean (true/false), got '{value}'"
            
            elif expected_type == int:
                int(value)
            
            elif expected_type == float:
                float(value)
            
            return None
            
        except ValueError:
            return f"{key}: Expected {expected_type.__name__}, got '{value}'"
    
    def _validate_range(
        self,
        value: str,
        min_val: Optional[float],
        max_val: Optional[float],
        key: str
    ) -> Optional[str]:
        """Validate numeric range"""
        try:
            num_value = float(value)
            
            if min_val is not None and num_value < min_val:
                return f"{key}: Value {num_value} is below minimum {min_val}"
            
            if max_val is not None and num_value > max_val:
                return f"{key}: Value {num_value} is above maximum {max_val}"
            
            return None
            
        except ValueError:
            return f"{key}: Expected numeric value, got '{value}'"
    
    def parse_config_file(self, file_path: Path) -> Dict:
        """
        Parse configuration file into dictionary
        
        Returns:
            Dict of {section: {key: value}}
        """
        try:
            parser = configparser.ConfigParser()
            parser.read(file_path, encoding='utf-8')
            
            result = {}
            for section in parser.sections():
                result[section] = dict(parser[section])
            
            return result
            
        except Exception as e:
            raise ConfigParseError(f"Failed to parse config: {e}")
    
    def merge_configs(
        self,
        default: ModConfig,
        override: ModConfig
    ) -> ModConfig:
        """
        Merge default and override configs
        
        Override values take precedence
        """
        try:
            # Parse both configs
            default_parser = configparser.ConfigParser()
            default_parser.read_string(default.content)
            
            override_parser = configparser.ConfigParser()
            override_parser.read_string(override.content)
            
            # Merge
            merged = configparser.ConfigParser()
            
            # Add all sections from default
            for section in default_parser.sections():
                merged.add_section(section)
                for key, value in default_parser[section].items():
                    merged.set(section, key, value)
            
            # Override with custom values
            for section in override_parser.sections():
                if not merged.has_section(section):
                    merged.add_section(section)
                
                for key, value in override_parser[section].items():
                    merged.set(section, key, value)
            
            # Convert back to string
            import io
            output = io.StringIO()
            merged.write(output)
            merged_content = output.getvalue()
            
            result = ModConfig(
                mod_id=override.mod_id,
                profile_name=override.profile_name,
                config_name=override.config_name,
                content=merged_content,
                is_custom=True
            )
            
            return result
            
        except Exception as e:
            raise ConfigError(f"Failed to merge configs: {e}")
    
    def get_config_summary(self, config: ModConfig) -> Dict:
        """
        Get summary of config values
        
        Returns:
            Dict with section counts and key counts
        """
        try:
            parser = configparser.ConfigParser()
            parser.read_string(config.content)
            
            summary = {
                'sections': len(parser.sections()),
                'total_keys': sum(len(parser[s]) for s in parser.sections()),
                'details': {}
            }
            
            for section in parser.sections():
                summary['details'][section] = len(parser[section])
            
            return summary
            
        except Exception as e:
            return {'error': str(e)}
    
    def find_configs_for_mod(self, mod_id: str) -> List[Path]:
        """Find all config files for a mod"""
        configs = []
        
        # Check default configs
        default_path = Settings.CONFIGS_DIR / "default" / mod_id
        if default_path.exists():
            configs.extend(default_path.glob("*.cfg"))
        
        # Check profile configs
        for profile_dir in Settings.CONFIGS_DIR.iterdir():
            if profile_dir.is_dir() and profile_dir.name != "default":
                mod_config_dir = profile_dir / mod_id
                if mod_config_dir.exists():
                    configs.extend(mod_config_dir.glob("*.cfg"))
        
        return configs
    
    def backup_config(self, config: ModConfig) -> Path:
        """Create backup of config file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{config.config_name}.{timestamp}.bak"
        
        backup_dir = Settings.BACKUPS_DIR / "configs" / config.profile_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_path = backup_dir / backup_name
        config.save_to_file(backup_path)
        
        self.logger.info(f"Created config backup: {backup_path}")
        return backup_path
    
    def restore_config_backup(
        self,
        backup_path: Path,
        mod_id: str,
        profile_name: str
    ) -> bool:
        """Restore config from backup"""
        try:
            config = ModConfig(
                mod_id=mod_id,
                profile_name=profile_name,
                config_name=backup_path.stem.split('.')[0]
            )
            config.load_from_file(backup_path)
            self.save_config(config)
            
            self.logger.info(f"Restored config from backup: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore config: {e}")
            return False
