"""
Mod Manager - Handle Mod Lifecycle and Processing
"""

import json
from pathlib import Path
from typing import Optional, Dict, List, Callable
from datetime import datetime

from core.database import Database
from core.models import Mod, ModDependency
from core.exceptions import (
    ModError,
    ModInstallError,
    ExtractionError
)
from utils.file_utils import ArchiveExtractor, TempDirectory
from utils.logger import LoggerMixin
from config.settings import Settings


class ModManager(LoggerMixin):
    """Manages mod lifecycle: download, extract, install, update"""
    
    def __init__(self, database: Database = None):
        self.db = database or Database()
        self.extractor = ArchiveExtractor()
    
    def install_mod(
        self,
        archive_path: Path,
        mod_data: Dict,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Mod:
        """
        Install mod from downloaded archive
        
        Args:
            archive_path: Path to downloaded ZIP file
            mod_data: Mod metadata from Thunderstore
            progress_callback: Optional progress callback
        
        Returns:
            Installed Mod object
        
        Raises:
            ModInstallError: If installation fails
        """
        try:
            self.logger.info(f"Installing mod: {mod_data['id']}")
            
            # Create mod directory
            mod_dir = Settings.MODS_DIR / mod_data['id'] / mod_data['version']
            mod_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract archive
            if progress_callback:
                progress_callback(0, 100, "Extracting archive...")
            
            with TempDirectory() as temp_dir:
                self.extractor.extract_zip(
                    archive_path,
                    temp_dir,
                    progress_callback=lambda c, t, f: progress_callback(
                        int((c / t) * 50), 100, f"Extracting: {f}"
                    ) if progress_callback else None
                )
                
                # Process extracted files
                if progress_callback:
                    progress_callback(50, 100, "Processing mod files...")
                
                mod = self._process_mod_files(temp_dir, mod_dir, mod_data)
            
            # Save to database
            if progress_callback:
                progress_callback(90, 100, "Saving to database...")
            
            mod.installed = True
            mod.downloaded_at = datetime.now()
            self.db.save_mod(mod)
            
            if progress_callback:
                progress_callback(100, 100, "Installation complete")
            
            self.logger.info(f"Mod installed successfully: {mod.id}")
            return mod
            
        except Exception as e:
            self.logger.error(f"Failed to install mod: {e}")
            raise ModInstallError(f"Installation failed: {e}")
    
    def _process_mod_files(
        self,
        source_dir: Path,
        target_dir: Path,
        mod_data: Dict
    ) -> Mod:
        """
        Process extracted mod files
        
        Organizes files and extracts metadata
        """
        # Find manifest.json
        manifest_path = self._find_file(source_dir, "manifest.json")
        if not manifest_path:
            raise ModInstallError("manifest.json not found in archive")
        
        # Parse manifest
        manifest = self._parse_manifest(manifest_path)
        
        # Create directory structure
        files_dir = target_dir / "files"
        configs_dir = target_dir / "configs"
        files_dir.mkdir(exist_ok=True)
        configs_dir.mkdir(exist_ok=True)
        
        # Extract icon
        icon_path = None
        icon_file = self._find_file(source_dir, "icon.png")
        if icon_file:
            icon_dest = target_dir / "icon.png"
            import shutil
            shutil.copy2(icon_file, icon_dest)
            icon_path = icon_dest
        
        # Extract README
        readme_path = None
        for readme_name in ["README.md", "readme.md", "ReadMe.md"]:
            readme_file = self._find_file(source_dir, readme_name)
            if readme_file:
                readme_dest = target_dir / "README.md"
                import shutil
                shutil.copy2(readme_file, readme_dest)
                readme_path = readme_dest
                break
        
        # Extract CHANGELOG
        changelog_path = None
        for changelog_name in ["CHANGELOG.md", "changelog.md", "CHANGES.md"]:
            changelog_file = self._find_file(source_dir, changelog_name)
            if changelog_file:
                changelog_dest = target_dir / "CHANGELOG.md"
                import shutil
                shutil.copy2(changelog_file, changelog_dest)
                changelog_path = changelog_dest
                break
        
        # Copy mod files (excluding metadata)
        config_files = []
        for item in source_dir.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(source_dir)
                
                # Skip metadata files
                if item.name in ['manifest.json', 'icon.png', 'README.md', 'CHANGELOG.md']:
                    continue
                
                # Detect config files
                if item.suffix in Settings.CONFIG_EXTENSIONS:
                    dest = configs_dir / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(item, dest)
                    config_files.append(item.name)
                else:
                    # Regular mod files
                    dest = files_dir / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(item, dest)
        
        # Parse dependencies
        dependencies = []
        for dep_string in manifest.get('dependencies', []):
            try:
                # Format: "Author-ModName-1.2.3"
                parts = dep_string.rsplit('-', 1)
                if len(parts) == 2:
                    mod_id = parts[0]
                    version = parts[1]
                    dependencies.append(
                        ModDependency(mod_id=mod_id, version_constraint=f">={version}")
                    )
            except Exception as e:
                self.logger.warning(f"Failed to parse dependency: {dep_string}")
        
        # Create Mod object
        mod = Mod(
            id=mod_data['id'],
            name=manifest.get('name', mod_data['name']),
            author=manifest.get('author', mod_data['author']),
            version=manifest.get('version_number', mod_data['version']),
            description=manifest.get('description', mod_data['description']),
            full_description=mod_data.get('full_description', ''),
            download_url=mod_data.get('download_url', ''),
            file_size=mod_data.get('file_size', 0),
            rating=mod_data.get('rating', 0.0),
            downloads=mod_data.get('downloads', 0),
            icon_path=icon_path,
            readme_path=readme_path,
            changelog_path=changelog_path,
            install_path=files_dir,
            manifest=manifest,
            dependencies=dependencies,
            config_files=config_files,
            tags=mod_data.get('categories', []),
        )
        
        return mod
    
    def _find_file(self, directory: Path, filename: str) -> Optional[Path]:
        """Find file in directory (case-insensitive)"""
        for item in directory.rglob('*'):
            if item.is_file() and item.name.lower() == filename.lower():
                return item
        return None
    
    def _parse_manifest(self, manifest_path: Path) -> Dict:
        """Parse manifest.json file"""
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ModInstallError(f"Failed to parse manifest: {e}")
    
    def update_mod(
        self,
        mod_id: str,
        new_archive_path: Path,
        new_mod_data: Dict,
        progress_callback: Optional[Callable] = None
    ) -> Mod:
        """
        Update existing mod to new version
        
        Args:
            mod_id: Current mod ID
            new_archive_path: Path to new version archive
            new_mod_data: New version metadata
            progress_callback: Optional progress callback
        
        Returns:
            Updated Mod object
        """
        try:
            self.logger.info(f"Updating mod: {mod_id}")
            
            # Get current mod
            current_mod = self.db.get_mod(mod_id)
            if not current_mod:
                raise ModError(f"Mod not found: {mod_id}")
            
            # Backup current version
            if progress_callback:
                progress_callback(0, 100, "Creating backup...")
            
            backup_dir = Settings.BACKUPS_DIR / "mods" / mod_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            from utils.file_utils import ArchiveExtractor
            backup_file = backup_dir / f"{current_mod.version}.zip"
            
            if current_mod.install_path and current_mod.install_path.exists():
                ArchiveExtractor.create_zip(
                    current_mod.install_path.parent,
                    backup_file
                )
            
            # Install new version
            new_mod = self.install_mod(
                new_archive_path,
                new_mod_data,
                progress_callback
            )
            
            # Keep user settings
            new_mod.enabled = current_mod.enabled
            new_mod.load_order = current_mod.load_order
            
            self.db.save_mod(new_mod)
            
            self.logger.info(f"Mod updated successfully: {mod_id}")
            return new_mod
            
        except Exception as e:
            self.logger.error(f"Failed to update mod: {e}")
            raise ModError(f"Update failed: {e}")
    
    def uninstall_mod(self, mod_id: str) -> bool:
        """
        Uninstall mod and remove files
        
        Args:
            mod_id: Mod to uninstall
        
        Returns:
            True if successful
        """
        try:
            self.logger.info(f"Uninstalling mod: {mod_id}")
            
            mod = self.db.get_mod(mod_id)
            if not mod:
                return False
            
            # Remove from database
            self.db.delete_mod(mod_id)
            
            # Remove files
            if mod.install_path:
                mod_root = mod.install_path.parent.parent  # Go up to mod ID dir
                if mod_root.exists():
                    import shutil
                    shutil.rmtree(mod_root)
            
            self.logger.info(f"Mod uninstalled: {mod_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to uninstall mod: {e}")
            return False
    
    def get_mod_info(self, mod_id: str) -> Optional[Mod]:
        """Get mod information"""
        return self.db.get_mod(mod_id)
    
    def get_all_installed_mods(self) -> List[Mod]:
        """Get all installed mods"""
        return self.db.get_all_mods(installed_only=True)
    
    def search_installed_mods(self, query: str) -> List[Mod]:
        """Search installed mods"""
        return self.db.search_mods(query)
    
    def verify_mod_integrity(self, mod_id: str) -> Tuple[bool, List[str]]:
        """
        Verify mod file integrity
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            mod = self.db.get_mod(mod_id)
            if not mod:
                return False, ["Mod not found in database"]
            
            # Check install path exists
            if not mod.install_path or not mod.install_path.exists():
                errors.append("Install path does not exist")
            
            # Check files exist
            if mod.install_path and mod.install_path.exists():
                files = list(mod.install_path.rglob('*'))
                if not files:
                    errors.append("No files found in install directory")
            
            # Check manifest
            if not mod.manifest:
                errors.append("Manifest data is missing")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            return False, [f"Verification failed: {e}"]
    
    def get_mod_size(self, mod_id: str) -> int:
        """Get total size of mod files in bytes"""
        mod = self.db.get_mod(mod_id)
        if not mod or not mod.install_path:
            return 0
        
        from utils.file_utils import FileOperations
        return FileOperations.get_directory_size(mod.install_path.parent)
    
    def export_mod_list(self, mods: List[Mod], output_path: Path):
        """Export mod list to JSON"""
        try:
            data = {
                'exported_at': datetime.now().isoformat(),
                'version': Settings.VERSION,
                'mods': [
                    {
                        'id': mod.id,
                        'name': mod.name,
                        'version': mod.version,
                        'author': mod.author,
                    }
                    for mod in mods
                ]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Exported {len(mods)} mods to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to export mod list: {e}")
            raise
    
    def import_mod_list(self, json_path: Path) -> List[str]:
        """
        Import mod list from JSON
        
        Returns:
            List of mod IDs to install
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            mod_ids = [mod['id'] for mod in data.get('mods', [])]
            
            self.logger.info(f"Imported {len(mod_ids)} mods from {json_path}")
            return mod_ids
            
        except Exception as e:
            self.logger.error(f"Failed to import mod list: {e}")
            raise
