"""
Core Data Models with Validation
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path
import json
from PyQt6.QtGui import QPixmap

from config.settings import Settings
from core.exceptions import ValidationError, InvalidModIDError


@dataclass
class ModDependency:
    """Represents a mod dependency"""
    mod_id: str
    version_constraint: str = "*"  # Semantic versioning constraint
    
    def __post_init__(self):
        if not self.mod_id:
            raise ValidationError("Dependency mod_id cannot be empty")
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ModDependency':
        return cls(**data)
    
    def is_satisfied_by(self, version: str) -> bool:
        """Check if given version satisfies this dependency"""
        # Simple version checking (can be enhanced with semantic versioning)
        if self.version_constraint == "*":
            return True
        return version == self.version_constraint


@dataclass
class Mod:
    """Represents a Valheim mod"""
    
    # Core attributes
    id: str  # author-modname
    name: str
    author: str
    version: str
    
    # Optional attributes
    description: str = ""
    full_description: str = ""
    download_url: str = ""
    file_size: int = 0
    rating: float = 0.0
    downloads: int = 0
    last_updated: Optional[datetime] = None
    
    # Local paths
    icon_path: Optional[Path] = None
    readme_path: Optional[Path] = None
    changelog_path: Optional[Path] = None
    install_path: Optional[Path] = None
    
    # Metadata
    manifest: Dict = field(default_factory=dict)
    dependencies: List[ModDependency] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # State
    enabled: bool = True
    load_order: int = 0
    installed: bool = False
    update_available: bool = False
    
    # Timestamps
    downloaded_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate mod data"""
        if not self.validate_mod_id(self.id):
            raise InvalidModIDError(f"Invalid mod ID: {self.id}")
        
        # Ensure paths are Path objects
        if self.icon_path and not isinstance(self.icon_path, Path):
            self.icon_path = Path(self.icon_path)
        if self.readme_path and not isinstance(self.readme_path, Path):
            self.readme_path = Path(self.readme_path)
        if self.changelog_path and not isinstance(self.changelog_path, Path):
            self.changelog_path = Path(self.changelog_path)
        if self.install_path and not isinstance(self.install_path, Path):
            self.install_path = Path(self.install_path)
    
    @staticmethod
    def validate_mod_id(mod_id: str) -> bool:
        """Validate mod ID format (author-modname)"""
        parts = mod_id.split('-', 1)
        return len(parts) == 2 and all(p.strip() for p in parts)
    
    def get_icon_pixmap(self, size: int = Settings.ICON_SIZE_MEDIUM) -> QPixmap:
        """Get mod icon as QPixmap"""
        if self.icon_path and self.icon_path.exists():
            pixmap = QPixmap(str(self.icon_path))
            if not pixmap.isNull():
                return pixmap.scaled(
                    size, size,
                    aspectRatioMode=1,  # KeepAspectRatio
                    transformMode=1     # SmoothTransformation
                )
        
        # Return default icon
        default_icon = Settings.RESOURCES_DIR / "icons" / "default_mod_icon.png"
        if default_icon.exists():
            return QPixmap(str(default_icon)).scaled(size, size, 1, 1)
        
        # Return empty pixmap as fallback
        return QPixmap(size, size)
    
    def get_readme_content(self) -> str:
        """Get README content"""
        if self.readme_path and self.readme_path.exists():
            try:
                return self.readme_path.read_text(encoding='utf-8')
            except Exception:
                return "Error reading README file"
        return "No README available"
    
    def get_changelog_content(self) -> str:
        """Get CHANGELOG content"""
        if self.changelog_path and self.changelog_path.exists():
            try:
                return self.changelog_path.read_text(encoding='utf-8')
            except Exception:
                return "Error reading CHANGELOG file"
        return "No CHANGELOG available"
    
    def has_dependency(self, mod_id: str) -> bool:
        """Check if this mod depends on another mod"""
        return any(dep.mod_id == mod_id for dep in self.dependencies)
    
    def get_file_list(self) -> List[Path]:
        """Get list of all files in this mod"""
        if not self.install_path or not self.install_path.exists():
            return []
        
        files = []
        for item in self.install_path.rglob('*'):
            if item.is_file():
                files.append(item)
        return files
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        data = asdict(self)
        
        # Convert Path objects to strings
        for key in ['icon_path', 'readme_path', 'changelog_path', 'install_path']:
            if data[key]:
                data[key] = str(data[key])
        
        # Convert datetime objects to ISO format
        for key in ['last_updated', 'downloaded_at', 'last_used']:
            if data[key]:
                data[key] = data[key].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Mod':
        """Create from dictionary"""
        # Convert string paths to Path objects
        for key in ['icon_path', 'readme_path', 'changelog_path', 'install_path']:
            if data.get(key):
                data[key] = Path(data[key])
        
        # Convert ISO strings to datetime objects
        for key in ['last_updated', 'downloaded_at', 'last_used']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        
        # Convert dependency dicts to objects
        if 'dependencies' in data:
            data['dependencies'] = [
                ModDependency.from_dict(dep) if isinstance(dep, dict) else dep
                for dep in data['dependencies']
            ]
        
        return cls(**data)


@dataclass
class Profile:
    """Represents a mod profile"""
    
    name: str
    mods: List[Mod] = field(default_factory=list)
    description: str = ""
    created: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    game_path: Optional[Path] = None
    active: bool = False
    
    def __post_init__(self):
        """Validate profile data"""
        if not self.name or len(self.name) < Settings.MIN_PROFILE_NAME_LENGTH:
            raise ValidationError(f"Profile name too short: {self.name}")
        
        if len(self.name) > Settings.MAX_PROFILE_NAME_LENGTH:
            raise ValidationError(f"Profile name too long: {self.name}")
        
        # Check for invalid characters
        for char in Settings.INVALID_PROFILE_CHARS:
            if char in self.name:
                raise ValidationError(f"Profile name contains invalid character: {char}")
        
        # Convert game_path to Path if needed
        if self.game_path and not isinstance(self.game_path, Path):
            self.game_path = Path(self.game_path)
    
    def add_mod(self, mod: Mod):
        """Add mod to profile"""
        if not any(m.id == mod.id for m in self.mods):
            self.mods.append(mod)
            self.last_modified = datetime.now()
    
    def remove_mod(self, mod_id: str):
        """Remove mod from profile"""
        self.mods = [m for m in self.mods if m.id != mod_id]
        self.last_modified = datetime.now()
    
    def get_mod(self, mod_id: str) -> Optional[Mod]:
        """Get mod by ID"""
        for mod in self.mods:
            if mod.id == mod_id:
                return mod
        return None
    
    def has_mod(self, mod_id: str) -> bool:
        """Check if profile has mod"""
        return any(m.id == mod_id for m in self.mods)
    
    def get_enabled_mods(self) -> List[Mod]:
        """Get list of enabled mods"""
        return [m for m in self.mods if m.enabled]
    
    def get_disabled_mods(self) -> List[Mod]:
        """Get list of disabled mods"""
        return [m for m in self.mods if not m.enabled]
    
    def reorder_mods(self, mod_id: str, new_position: int):
        """Change mod load order"""
        mod = self.get_mod(mod_id)
        if mod:
            self.mods.remove(mod)
            self.mods.insert(new_position, mod)
            # Update load order values
            for i, m in enumerate(self.mods):
                m.load_order = i
            self.last_modified = datetime.now()
    
    def sort_by_dependencies(self):
        """Sort mods by dependency order (topological sort)"""
        from services.dependency_resolver import DependencyResolver
        resolver = DependencyResolver()
        sorted_ids = resolver.resolve_load_order(self.mods)
        
        # Reorder mods list
        sorted_mods = []
        for mod_id in sorted_ids:
            mod = self.get_mod(mod_id)
            if mod:
                sorted_mods.append(mod)
        
        self.mods = sorted_mods
        for i, mod in enumerate(self.mods):
            mod.load_order = i
    
    def export_to_json(self, path: Path):
        """Export profile to JSON file"""
        data = self.to_dict()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def import_from_json(cls, path: Path) -> 'Profile':
        """Import profile from JSON file"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def clone(self, new_name: str) -> 'Profile':
        """Create a copy of this profile"""
        return Profile(
            name=new_name,
            mods=[Mod.from_dict(m.to_dict()) for m in self.mods],
            description=self.description,
            game_path=self.game_path
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'mods': [m.to_dict() for m in self.mods],
            'description': self.description,
            'created': self.created.isoformat(),
            'last_modified': self.last_modified.isoformat(),
            'game_path': str(self.game_path) if self.game_path else None,
            'active': self.active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Profile':
        """Create from dictionary"""
        data['mods'] = [Mod.from_dict(m) for m in data.get('mods', [])]
        data['created'] = datetime.fromisoformat(data['created'])
        data['last_modified'] = datetime.fromisoformat(data['last_modified'])
        if data.get('game_path'):
            data['game_path'] = Path(data['game_path'])
        return cls(**data)


@dataclass
class ModConfig:
    """Represents a mod configuration"""
    
    mod_id: str
    profile_name: str
    config_name: str
    content: str = ""
    is_custom: bool = False
    last_modified: datetime = field(default_factory=datetime.now)
    
    def load_from_file(self, path: Path):
        """Load config from file"""
        if path.exists():
            self.content = path.read_text(encoding='utf-8')
            self.last_modified = datetime.now()
    
    def save_to_file(self, path: Path):
        """Save config to file"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.content, encoding='utf-8')
        self.last_modified = datetime.now()
    
    def reset_to_default(self, default_content: str):
        """Reset to default configuration"""
        self.content = default_content
        self.is_custom = False
        self.last_modified = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'mod_id': self.mod_id,
            'profile_name': self.profile_name,
            'config_name': self.config_name,
            'content': self.content,
            'is_custom': self.is_custom,
            'last_modified': self.last_modified.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ModConfig':
        """Create from dictionary"""
        data['last_modified'] = datetime.fromisoformat(data['last_modified'])
        return cls(**data)
