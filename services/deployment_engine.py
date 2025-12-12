"""
Smart Deployment Engine with Hash-Based Change Detection
Only copies changed files for efficient deployment
"""

import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

from core.models import Profile, Mod
from core.database import Database
from core.exceptions import (
    DeploymentError,
    DeploymentFailedError,
    GamePathInvalidError,
    BepInExNotFoundError,
    RollbackError,
    with_rollback
)
from utils.hash_utils import calculate_file_hash, HashCache
from utils.file_utils import copy_with_progress, safe_remove_directory
from utils.logger import LoggerMixin
from config.settings import Settings


class DeploymentCheckpoint:
    """Represents a deployment state that can be rolled back"""
    
    def __init__(self, profile_name: str, game_path: Path):
        self.profile_name = profile_name
        self.game_path = game_path
        self.timestamp = datetime.now()
        self.backup_path = Settings.BACKUPS_DIR / f"checkpoint_{self.timestamp.strftime('%Y%m%d_%H%M%S')}"
        self.deployment_state = {}
        self.files_modified = []
    
    def save(self, deployment_state: Dict, files: List[Path]):
        """Save checkpoint data"""
        self.deployment_state = deployment_state.copy()
        self.files_modified = [str(f) for f in files]
        
        # Save checkpoint metadata
        checkpoint_file = self.backup_path / "checkpoint.json"
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(checkpoint_file, 'w') as f:
            json.dump({
                'profile_name': self.profile_name,
                'game_path': str(self.game_path),
                'timestamp': self.timestamp.isoformat(),
                'deployment_state': self.deployment_state,
                'files_modified': self.files_modified
            }, f, indent=2)
    
    @classmethod
    def load(cls, backup_path: Path) -> 'DeploymentCheckpoint':
        """Load checkpoint from backup"""
        checkpoint_file = backup_path / "checkpoint.json"
        
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        checkpoint = cls(data['profile_name'], Path(data['game_path']))
        checkpoint.timestamp = datetime.fromisoformat(data['timestamp'])
        checkpoint.backup_path = backup_path
        checkpoint.deployment_state = data['deployment_state']
        checkpoint.files_modified = data['files_modified']
        
        return checkpoint


class DeploymentEngine(LoggerMixin):
    """Manages smart mod deployment with hash tracking"""
    
    def __init__(self, database: Database = None):
        self.db = database or Database()
        self.hash_cache = HashCache()
        self.current_checkpoint: Optional[DeploymentCheckpoint] = None
    
    def validate_game_path(self, game_path: Path) -> bool:
        """Validate that game path contains Valheim installation"""
        if not game_path.exists():
            raise GamePathInvalidError(f"Game path does not exist: {game_path}")
        
        # Check for valheim.exe or valheim binary
        exe_names = ['valheim.exe', 'valheim', 'valheim.x86_64']
        has_exe = any((game_path / exe).exists() for exe in exe_names)
        
        if not has_exe:
            raise GamePathInvalidError(
                f"Game executable not found in: {game_path}"
            )
        
        # Check for BepInEx directory
        bepinex_path = game_path / "BepInEx"
        if not bepinex_path.exists():
            self.logger.warning("BepInEx not found, it will be installed")
        
        return True
    
    def create_checkpoint(self, profile: Profile) -> DeploymentCheckpoint:
        """Create deployment checkpoint for rollback"""
        if not profile.game_path:
            raise DeploymentError("Profile has no game path set")
        
        checkpoint = DeploymentCheckpoint(profile.name, profile.game_path)
        
        # Get current deployment state
        deployment_state = self.db.get_deployment_state(profile.name)
        
        # Backup currently deployed files
        backup_files = []
        for file_path in deployment_state.keys():
            src = Path(file_path)
            if src.exists():
                rel_path = src.relative_to(profile.game_path)
                dst = checkpoint.backup_path / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                backup_files.append(src)
        
        checkpoint.save(deployment_state, backup_files)
        self.logger.info(f"Created checkpoint: {checkpoint.backup_path}")
        
        return checkpoint
    
    @with_rollback
    def deploy_profile(
        self,
        profile: Profile,
        progress_callback=None
    ) -> bool:
        """
        Deploy profile to game directory with smart copying
        
        Args:
            profile: Profile to deploy
            progress_callback: Optional callback(current, total, message)
        
        Returns:
            True if successful
        
        Raises:
            DeploymentFailedError: If deployment fails
        """
        if not profile.game_path:
            raise DeploymentError("Profile has no game path set")
        
        self.validate_game_path(profile.game_path)
        
        self.logger.info(f"Starting deployment of profile: {profile.name}")
        
        # Create checkpoint for rollback
        if Settings.AUTO_BACKUP_BEFORE_DEPLOY:
            self.current_checkpoint = self.create_checkpoint(profile)
        
        try:
            # Get enabled mods in correct load order
            enabled_mods = profile.get_enabled_mods()
            if not enabled_mods:
                self.logger.warning("No enabled mods in profile")
                return True
            
            # Sort by load order
            enabled_mods.sort(key=lambda m: m.load_order)
            
            self.logger.info(f"Deploying {len(enabled_mods)} mods")
            
            # Calculate what needs to be deployed
            changes = self.calculate_changes(profile, enabled_mods)
            
            total_operations = (
                len(changes['to_add']) +
                len(changes['to_update']) +
                len(changes['to_remove'])
            )
            
            current_operation = 0
            
            # Remove files from disabled/removed mods
            for file_path in changes['to_remove']:
                if progress_callback:
                    progress_callback(
                        current_operation,
                        total_operations,
                        f"Removing: {Path(file_path).name}"
                    )
                
                self._remove_file(file_path)
                current_operation += 1
            
            # Deploy mods
            plugins_dir = profile.game_path / Settings.BEPINEX_PLUGINS_DIR
            plugins_dir.mkdir(parents=True, exist_ok=True)
            
            for mod in enabled_mods:
                if not mod.install_path or not mod.install_path.exists():
                    self.logger.warning(f"Mod {mod.id} has no install path")
                    continue
                
                # Copy mod files
                mod_files = self._get_mod_files(mod)
                
                for src_file in mod_files:
                    rel_path = src_file.relative_to(mod.install_path)
                    dst_file = plugins_dir / mod.id / rel_path
                    
                    # Check if file needs to be copied
                    if self._should_copy_file(src_file, dst_file):
                        if progress_callback:
                            progress_callback(
                                current_operation,
                                total_operations,
                                f"Copying: {mod.name} - {rel_path.name}"
                            )
                        
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                        
                        # Update deployment state
                        file_hash = calculate_file_hash(src_file)
                        self.db.save_deployment_state(
                            str(dst_file),
                            file_hash,
                            mod.id,
                            profile.name
                        )
                        
                        current_operation += 1
            
            # Deploy configs
            self._deploy_configs(profile, progress_callback)
            
            self.logger.info(f"Profile {profile.name} deployed successfully")
            
            # Mark profile as active
            profile.active = True
            
            return True
            
        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            raise DeploymentFailedError(f"Deployment failed: {e}")
    
    def calculate_changes(
        self,
        profile: Profile,
        mods: List[Mod]
    ) -> Dict[str, List]:
        """
        Calculate what files need to be added/updated/removed
        
        Returns:
            Dict with 'to_add', 'to_update', 'to_remove' lists
        """
        current_state = self.db.get_deployment_state(profile.name)
        new_state = {}
        
        # Build new state from enabled mods
        for mod in mods:
            if not mod.install_path or not mod.install_path.exists():
                continue
            
            mod_files = self._get_mod_files(mod)
            plugins_dir = profile.game_path / Settings.BEPINEX_PLUGINS_DIR
            
            for src_file in mod_files:
                rel_path = src_file.relative_to(mod.install_path)
                dst_file = plugins_dir / mod.id / rel_path
                file_hash = calculate_file_hash(src_file)
                new_state[str(dst_file)] = file_hash
        
        # Compare states
        to_add = []
        to_update = []
        to_remove = []
        
        # Find files to add or update
        for file_path, file_hash in new_state.items():
            if file_path not in current_state:
                to_add.append(file_path)
            elif current_state[file_path] != file_hash:
                to_update.append(file_path)
        
        # Find files to remove
        for file_path in current_state:
            if file_path not in new_state:
                to_remove.append(file_path)
        
        self.logger.info(
            f"Changes: {len(to_add)} to add, "
            f"{len(to_update)} to update, "
            f"{len(to_remove)} to remove"
        )
        
        return {
            'to_add': to_add,
            'to_update': to_update,
            'to_remove': to_remove
        }
    
    def _should_copy_file(self, src: Path, dst: Path) -> bool:
        """Check if file needs to be copied based on hash"""
        if not dst.exists():
            return True
        
        src_hash = calculate_file_hash(src)
        dst_hash = calculate_file_hash(dst)
        
        return src_hash != dst_hash
    
    def _get_mod_files(self, mod: Mod) -> List[Path]:
        """Get all deployable files from mod"""
        if not mod.install_path or not mod.install_path.exists():
            return []
        
        files = []
        for item in mod.install_path.rglob('*'):
            if item.is_file():
                # Skip metadata files
                if item.name in ['manifest.json', 'icon.png', 'README.md', 'CHANGELOG.md']:
                    continue
                files.append(item)
        
        return files
    
    def _remove_file(self, file_path: str):
        """Safely remove deployed file"""
        path = Path(file_path)
        if path.exists():
            try:
                path.unlink()
                self.logger.debug(f"Removed: {file_path}")
                
                # Remove empty parent directories
                parent = path.parent
                while parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
                    
            except Exception as e:
                self.logger.warning(f"Failed to remove {file_path}: {e}")
    
    def _deploy_configs(self, profile: Profile, progress_callback=None):
        """Deploy configuration files"""
        from services.config_manager import ConfigManager
        
        config_manager = ConfigManager(self.db)
        config_dir = profile.game_path / Settings.BEPINEX_CONFIG_DIR
        config_dir.mkdir(parents=True, exist_ok=True)
        
        for mod in profile.get_enabled_mods():
            for config_name in mod.config_files:
                try:
                    config = config_manager.load_config(mod.id, profile.name)
                    if config:
                        dst_path = config_dir / config_name
                        config.save_to_file(dst_path)
                        self.logger.debug(f"Deployed config: {config_name}")
                except Exception as e:
                    self.logger.warning(f"Failed to deploy config {config_name}: {e}")
    
    def clear_deployment(self, profile: Profile) -> bool:
        """Remove all deployed files for profile"""
        if not profile.game_path:
            return False
        
        self.logger.info(f"Clearing deployment for profile: {profile.name}")
        
        try:
            deployment_state = self.db.get_deployment_state(profile.name)
            
            for file_path in deployment_state.keys():
                self._remove_file(file_path)
            
            # Clear database state
            self.db.clear_deployment_state(profile.name)
            
            # Mark profile as inactive
            profile.active = False
            
            self.logger.info("Deployment cleared successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear deployment: {e}")
            return False
    
    def rollback(self, checkpoint: DeploymentCheckpoint = None) -> bool:
        """Rollback to previous deployment state"""
        checkpoint = checkpoint or self.current_checkpoint
        
        if not checkpoint:
            raise RollbackError("No checkpoint available for rollback")
        
        self.logger.info(f"Rolling back to checkpoint: {checkpoint.timestamp}")
        
        try:
            # Clear current deployment
            current_state = self.db.get_deployment_state(checkpoint.profile_name)
            for file_path in current_state.keys():
                self._remove_file(file_path)
            
            # Restore files from backup
            if checkpoint.backup_path.exists():
                for backup_file in checkpoint.backup_path.rglob('*'):
                    if backup_file.is_file() and backup_file.name != 'checkpoint.json':
                        rel_path = backup_file.relative_to(checkpoint.backup_path)
                        dst_file = checkpoint.game_path / rel_path
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(backup_file, dst_file)
            
            # Restore deployment state in database
            self.db.clear_deployment_state(checkpoint.profile_name)
            for file_path, file_hash in checkpoint.deployment_state.items():
                self.db.save_deployment_state(
                    file_path,
                    file_hash,
                    '',  # mod_id unknown after rollback
                    checkpoint.profile_name
                )
            
            self.logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            raise RollbackError(f"Rollback failed: {e}")
    
    def get_deployment_info(self, profile: Profile) -> Dict:
        """Get information about current deployment"""
        deployment_state = self.db.get_deployment_state(profile.name)
        
        return {
            'profile_name': profile.name,
            'files_deployed': len(deployment_state),
            'total_size': sum(
                Path(fp).stat().st_size
                for fp in deployment_state.keys()
                if Path(fp).exists()
            ),
            'active': profile.active
        }
