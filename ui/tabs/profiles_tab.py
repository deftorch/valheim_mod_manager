"""
Profiles Tab - Create and Manage Mod Profiles
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
    QCheckBox, QMessageBox, QInputDialog, QFileDialog,
    QMenu, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from pathlib import Path
from datetime import datetime

from core.database import Database
from core.models import Profile, Mod
from services.deployment_engine import DeploymentEngine
from services.dependency_resolver import DependencyResolver
from utils.logger import LoggerMixin
from config.settings import Settings


class ProfileEditorDialog(QDialog):
    """Dialog for creating/editing profiles"""
    
    def __init__(self, profile: Profile = None, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.is_new = profile is None
        
        self.setup_ui()
        
        if not self.is_new:
            self.load_profile_data()
    
    def setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle("New Profile" if self.is_new else "Edit Profile")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Name input
        name_label = QLabel("Profile Name:")
        layout.addWidget(name_label)
        
        from PyQt6.QtWidgets import QLineEdit
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter profile name...")
        layout.addWidget(self.name_input)
        
        # Description input
        desc_label = QLabel("Description (optional):")
        layout.addWidget(desc_label)
        
        from PyQt6.QtWidgets import QTextEdit
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Enter profile description...")
        self.desc_input.setMaximumHeight(100)
        layout.addWidget(self.desc_input)
        
        # Game path input
        game_path_label = QLabel("Game Path (optional):")
        layout.addWidget(game_path_label)
        
        game_path_widget = QWidget()
        game_path_layout = QHBoxLayout(game_path_widget)
        game_path_layout.setContentsMargins(0, 0, 0, 0)
        
        self.game_path_input = QLineEdit()
        self.game_path_input.setPlaceholderText("Auto-detect or browse...")
        game_path_layout.addWidget(self.game_path_input)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_game_path)
        game_path_layout.addWidget(browse_btn)
        
        layout.addWidget(game_path_widget)
        
        # Buttons
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        buttons_layout.addWidget(save_btn)
        
        layout.addWidget(buttons_widget)
    
    def load_profile_data(self):
        """Load existing profile data"""
        if self.profile:
            self.name_input.setText(self.profile.name)
            self.desc_input.setPlainText(self.profile.description)
            if self.profile.game_path:
                self.game_path_input.setText(str(self.profile.game_path))
    
    def browse_game_path(self):
        """Browse for game directory"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Valheim Installation Directory",
            str(Path.home())
        )
        
        if path:
            self.game_path_input.setText(path)
    
    def get_profile_data(self) -> dict:
        """Get profile data from inputs"""
        game_path = self.game_path_input.text().strip()
        
        return {
            'name': self.name_input.text().strip(),
            'description': self.desc_input.toPlainText().strip(),
            'game_path': Path(game_path) if game_path else None
        }


class ProfilesTab(QWidget, LoggerMixin):
    """Manage mod profiles"""
    
    profile_created = pyqtSignal(str)  # profile_name
    profile_deleted = pyqtSignal(str)  # profile_name
    profile_activated = pyqtSignal(str)  # profile_name
    
    def __init__(self, database: Database, deployment_engine: DeploymentEngine):
        super().__init__()
        self.db = database
        self.deployment_engine = deployment_engine
        self.dependency_resolver = DependencyResolver()
        
        self.profiles = []
        self.current_profile = None
        self.available_mods = []
        
        self.setup_ui()
        self.load_profiles()
        self.load_available_mods()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Profile list
        left_panel = self.create_profile_list()
        splitter.addWidget(left_panel)
        
        # Right panel - Mods in profile
        right_panel = self.create_mods_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([250, 750])
        layout.addWidget(splitter)
    
    def create_header(self) -> QWidget:
        """Create header with profile count"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.count_label = QLabel("Profiles: 0")
        self.count_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.count_label)
        
        layout.addStretch()
        
        return widget
    
    def create_profile_list(self) -> QWidget:
        """Create profile list panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("<h3>Profiles</h3>")
        layout.addWidget(title)
        
        # List widget
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self.on_profile_selected)
        layout.addWidget(self.profile_list)
        
        # Action buttons
        buttons_widget = QWidget()
        buttons_layout = QVBoxLayout(buttons_widget)
        
        new_btn = QPushButton("➕ New Profile")
        new_btn.clicked.connect(self.create_profile)
        buttons_layout.addWidget(new_btn)
        
        clone_btn = QPushButton("📋 Clone")
        clone_btn.clicked.connect(self.clone_profile)
        buttons_layout.addWidget(clone_btn)
        
        edit_btn = QPushButton("✏️ Edit")
        edit_btn.clicked.connect(self.edit_profile)
        buttons_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self.delete_profile)
        buttons_layout.addWidget(delete_btn)
        
        buttons_layout.addSpacing(10)
        
        export_btn = QPushButton("📤 Export")
        export_btn.clicked.connect(self.export_profile)
        buttons_layout.addWidget(export_btn)
        
        import_btn = QPushButton("📥 Import")
        import_btn.clicked.connect(self.import_profile)
        buttons_layout.addWidget(import_btn)
        
        layout.addWidget(buttons_widget)
        
        return widget
    
    def create_mods_panel(self) -> QWidget:
        """Create mods in profile panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        
        self.profile_title = QLabel("<h3>Select a profile</h3>")
        header_layout.addWidget(self.profile_title)
        
        header_layout.addStretch()
        
        self.mod_count_label = QLabel("Mods: 0")
        header_layout.addWidget(self.mod_count_label)
        
        layout.addWidget(header_widget)
        
        # Mods list
        self.mods_list = QListWidget()
        self.mods_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.mods_list)
        
        # Action buttons
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        
        add_btn = QPushButton("➕ Add Mods")
        add_btn.clicked.connect(self.add_mods_to_profile)
        buttons_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("➖ Remove")
        remove_btn.clicked.connect(self.remove_mods_from_profile)
        buttons_layout.addWidget(remove_btn)
        
        toggle_btn = QPushButton("⚡ Toggle Enable")
        toggle_btn.clicked.connect(self.toggle_mod_enabled)
        buttons_layout.addWidget(toggle_btn)
        
        buttons_layout.addStretch()
        
        reorder_up_btn = QPushButton("↑ Up")
        reorder_up_btn.clicked.connect(self.move_mod_up)
        buttons_layout.addWidget(reorder_up_btn)
        
        reorder_down_btn = QPushButton("↓ Down")
        reorder_down_btn.clicked.connect(self.move_mod_down)
        buttons_layout.addWidget(reorder_down_btn)
        
        sort_btn = QPushButton("🔀 Sort by Dependencies")
        sort_btn.clicked.connect(self.sort_by_dependencies)
        buttons_layout.addWidget(sort_btn)
        
        layout.addWidget(buttons_widget)
        
        return widget
    
    def load_profiles(self):
        """Load profiles from storage"""
        try:
            self.profiles.clear()
            self.profile_list.clear()
            
            profiles_dir = Settings.PROFILES_DIR
            profiles_dir.mkdir(parents=True, exist_ok=True)
            
            for profile_file in profiles_dir.glob("*.json"):
                try:
                    profile = Profile.import_from_json(profile_file)
                    self.profiles.append(profile)
                    
                    item = QListWidgetItem()
                    
                    # Active indicator
                    prefix = "• " if profile.active else "○ "
                    text = f"{prefix}{profile.name}"
                    
                    if profile.mods:
                        text += f" ({len(profile.mods)})"
                    
                    item.setText(text)
                    item.setData(Qt.ItemDataRole.UserRole, profile)
                    
                    self.profile_list.addItem(item)
                    
                except Exception as e:
                    self.logger.error(f"Failed to load profile {profile_file}: {e}")
            
            self.count_label.setText(f"Profiles: {len(self.profiles)}")
            
        except Exception as e:
            self.logger.error(f"Failed to load profiles: {e}")
    
    def load_available_mods(self):
        """Load available mods from repository"""
        self.available_mods = self.db.get_all_mods(installed_only=True)
    
    def on_profile_selected(self, current, previous):
        """Handle profile selection"""
        if not current:
            return
        
        profile = current.data(Qt.ItemDataRole.UserRole)
        self.current_profile = profile
        
        # Update display
        self.update_mods_display()
    
    def update_mods_display(self):
        """Update mods display for current profile"""
        if not self.current_profile:
            return
        
        self.profile_title.setText(f"<h3>{self.current_profile.name}</h3>")
        
        self.mods_list.clear()
        
        for mod in self.current_profile.mods:
            item = QListWidgetItem()
            
            # Checkbox-like display
            enabled_icon = "☑️" if mod.enabled else "☐"
            text = f"{enabled_icon} 🎨 {mod.name} v{mod.version}"
            
            if mod.update_available:
                text += " ⬆️"
            
            item.setText(text)
            item.setData(Qt.ItemDataRole.UserRole, mod)
            
            self.mods_list.addItem(item)
        
        self.mod_count_label.setText(f"Mods: {len(self.current_profile.mods)}")
    
    def create_profile(self):
        """Create new profile"""
        dialog = ProfileEditorDialog(parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_profile_data()
            
            if not data['name']:
                QMessageBox.warning(self, "Invalid Name", "Profile name cannot be empty")
                return
            
            # Check if name already exists
            if any(p.name == data['name'] for p in self.profiles):
                QMessageBox.warning(
                    self,
                    "Duplicate Name",
                    f"Profile '{data['name']}' already exists"
                )
                return
            
            try:
                # Create profile
                profile = Profile(
                    name=data['name'],
                    description=data['description'],
                    game_path=data['game_path']
                )
                
                # Save to file
                profile_file = Settings.PROFILES_DIR / f"{profile.name}.json"
                profile.export_to_json(profile_file)
                
                self.logger.info(f"Created profile: {profile.name}")
                
                # Reload profiles
                self.load_profiles()
                
                # Emit signal
                self.profile_created.emit(profile.name)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Profile '{profile.name}' created successfully"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to create profile: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create profile:\n{str(e)}"
                )
    
    def clone_profile(self):
        """Clone current profile"""
        if not self.current_profile:
            QMessageBox.warning(self, "No Profile", "Please select a profile to clone")
            return
        
        name, ok = QInputDialog.getText(
            self,
            "Clone Profile",
            f"Enter name for cloned profile:",
            text=f"{self.current_profile.name} (Copy)"
        )
        
        if ok and name:
            try:
                cloned = self.current_profile.clone(name)
                
                # Save to file
                profile_file = Settings.PROFILES_DIR / f"{cloned.name}.json"
                cloned.export_to_json(profile_file)
                
                self.load_profiles()
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Profile cloned as '{name}'"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to clone profile: {e}")
                QMessageBox.critical(self, "Error", f"Failed to clone:\n{str(e)}")
    
    def edit_profile(self):
        """Edit current profile"""
        if not self.current_profile:
            return
        
        dialog = ProfileEditorDialog(self.current_profile, parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_profile_data()
            
            try:
                # Update profile
                old_name = self.current_profile.name
                self.current_profile.name = data['name']
                self.current_profile.description = data['description']
                self.current_profile.game_path = data['game_path']
                self.current_profile.last_modified = datetime.now()
                
                # Save
                profile_file = Settings.PROFILES_DIR / f"{self.current_profile.name}.json"
                self.current_profile.export_to_json(profile_file)
                
                # Delete old file if name changed
                if old_name != self.current_profile.name:
                    old_file = Settings.PROFILES_DIR / f"{old_name}.json"
                    if old_file.exists():
                        old_file.unlink()
                
                self.load_profiles()
                
                QMessageBox.information(self, "Success", "Profile updated successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to edit profile: {e}")
                QMessageBox.critical(self, "Error", f"Failed to edit:\n{str(e)}")
    
    def delete_profile(self):
        """Delete current profile"""
        if not self.current_profile:
            return
        
        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Are you sure you want to delete profile '{self.current_profile.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                profile_file = Settings.PROFILES_DIR / f"{self.current_profile.name}.json"
                if profile_file.exists():
                    profile_file.unlink()
                
                self.logger.info(f"Deleted profile: {self.current_profile.name}")
                
                name = self.current_profile.name
                self.current_profile = None
                
                self.load_profiles()
                
                self.profile_deleted.emit(name)
                
                QMessageBox.information(self, "Success", "Profile deleted")
                
            except Exception as e:
                self.logger.error(f"Failed to delete profile: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete:\n{str(e)}")
    
    def add_mods_to_profile(self):
        """Add mods to current profile"""
        if not self.current_profile:
            QMessageBox.warning(self, "No Profile", "Please select a profile first")
            return
        
        # TODO: Show mod selection dialog
        QMessageBox.information(self, "Add Mods", "Mod selection dialog not yet implemented")
    
    def remove_mods_from_profile(self):
        """Remove selected mods from profile"""
        if not self.current_profile:
            return
        
        selected_items = self.mods_list.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            mod = item.data(Qt.ItemDataRole.UserRole)
            self.current_profile.remove_mod(mod.id)
        
        self.save_current_profile()
        self.update_mods_display()
    
    def toggle_mod_enabled(self):
        """Toggle enabled state of selected mods"""
        if not self.current_profile:
            return
        
        selected_items = self.mods_list.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            mod = item.data(Qt.ItemDataRole.UserRole)
            mod.enabled = not mod.enabled
        
        self.save_current_profile()
        self.update_mods_display()
    
    def move_mod_up(self):
        """Move selected mod up in load order"""
        # TODO: Implement reordering
        pass
    
    def move_mod_down(self):
        """Move selected mod down in load order"""
        # TODO: Implement reordering
        pass
    
    def sort_by_dependencies(self):
        """Sort mods by dependency order"""
        if not self.current_profile:
            return
        
        try:
            self.current_profile.sort_by_dependencies()
            self.save_current_profile()
            self.update_mods_display()
            
            QMessageBox.information(
                self,
                "Success",
                "Mods sorted by dependency order"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to sort: {e}")
            QMessageBox.critical(self, "Error", f"Failed to sort:\n{str(e)}")
    
    def export_profile(self):
        """Export profile to file"""
        if not self.current_profile:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profile",
            str(Settings.PROFILES_DIR / f"{self.current_profile.name}.json"),
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                self.current_profile.export_to_json(Path(file_path))
                QMessageBox.information(self, "Success", "Profile exported")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")
    
    def import_profile(self):
        """Import profile from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Profile",
            str(Settings.PROFILES_DIR),
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                profile = Profile.import_from_json(Path(file_path))
                
                # Save to profiles directory
                profile_file = Settings.PROFILES_DIR / f"{profile.name}.json"
                profile.export_to_json(profile_file)
                
                self.load_profiles()
                
                QMessageBox.information(self, "Success", "Profile imported")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Import failed:\n{str(e)}")
    
    def save_current_profile(self):
        """Save current profile to file"""
        if not self.current_profile:
            return
        
        try:
            profile_file = Settings.PROFILES_DIR / f"{self.current_profile.name}.json"
            self.current_profile.export_to_json(profile_file)
        except Exception as e:
            self.logger.error(f"Failed to save profile: {e}")
    
    def set_current_profile(self, profile: Profile):
        """Set current profile externally"""
        self.current_profile = profile
        self.update_mods_display()
