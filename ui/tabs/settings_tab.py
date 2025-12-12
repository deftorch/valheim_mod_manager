"""
Settings Tab - Application Settings and Preferences
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QSpinBox,
    QCheckBox, QComboBox, QFileDialog, QMessageBox,
    QScrollArea, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path

from core.database import Database
from services.game_launcher import GameLauncher
from utils.logger import LoggerMixin, cleanup_old_logs
from config.settings import Settings


class SettingsTab(QWidget, LoggerMixin):
    """Application settings and preferences"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, database: Database):
        super().__init__()
        self.db = database
        self.game_launcher = GameLauncher()
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup user interface"""
        # Main scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Content widget
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # Title
        title = QLabel("<h2>⚙️ Settings</h2>")
        layout.addWidget(title)
        
        # Game settings
        game_group = self.create_game_settings()
        layout.addWidget(game_group)
        
        # Download settings
        download_group = self.create_download_settings()
        layout.addWidget(download_group)
        
        # UI settings
        ui_group = self.create_ui_settings()
        layout.addWidget(ui_group)
        
        # Advanced settings
        advanced_group = self.create_advanced_settings()
        layout.addWidget(advanced_group)
        
        # About section
        about_group = self.create_about_section()
        layout.addWidget(about_group)
        
        layout.addStretch()
        
        # Save button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        scroll.setWidget(content)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def create_game_settings(self) -> QGroupBox:
        """Create game settings group"""
        group = QGroupBox("🎮 Game Settings")
        layout = QFormLayout()
        
        # Game path
        game_path_widget = QWidget()
        game_path_layout = QHBoxLayout(game_path_widget)
        game_path_layout.setContentsMargins(0, 0, 0, 0)
        
        self.game_path_input = QLineEdit()
        self.game_path_input.setPlaceholderText("Auto-detect or browse...")
        game_path_layout.addWidget(self.game_path_input)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_game_path)
        game_path_layout.addWidget(browse_btn)
        
        detect_btn = QPushButton("🔍 Auto-detect")
        detect_btn.clicked.connect(self.auto_detect_game)
        game_path_layout.addWidget(detect_btn)
        
        layout.addRow("Game Path:", game_path_widget)
        
        # Launch options
        self.console_checkbox = QCheckBox("Enable debug console (F5)")
        layout.addRow("Launch Options:", self.console_checkbox)
        
        self.skipintro_checkbox = QCheckBox("Skip intro video")
        layout.addRow("", self.skipintro_checkbox)
        
        self.windowed_checkbox = QCheckBox("Run in windowed mode")
        layout.addRow("", self.windowed_checkbox)
        
        # Launch via Steam
        self.steam_launch_checkbox = QCheckBox(
            "Launch via Steam (recommended for better integration)"
        )
        layout.addRow("", self.steam_launch_checkbox)
        
        group.setLayout(layout)
        return group
    
    def create_download_settings(self) -> QGroupBox:
        """Create download settings group"""
        group = QGroupBox("📥 Download Settings")
        layout = QFormLayout()
        
        # Concurrent downloads
        self.concurrent_downloads_spin = QSpinBox()
        self.concurrent_downloads_spin.setMinimum(1)
        self.concurrent_downloads_spin.setMaximum(10)
        self.concurrent_downloads_spin.setValue(Settings.MAX_CONCURRENT_DOWNLOADS)
        layout.addRow("Max Concurrent Downloads:", self.concurrent_downloads_spin)
        
        # Cache duration
        self.cache_duration_spin = QSpinBox()
        self.cache_duration_spin.setMinimum(1)
        self.cache_duration_spin.setMaximum(48)
        self.cache_duration_spin.setSuffix(" hours")
        self.cache_duration_spin.setValue(Settings.CACHE_DURATION_HOURS)
        layout.addRow("Cache Duration:", self.cache_duration_spin)
        
        # Network timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(10)
        self.timeout_spin.setMaximum(120)
        self.timeout_spin.setSuffix(" seconds")
        self.timeout_spin.setValue(Settings.REQUEST_TIMEOUT)
        layout.addRow("Network Timeout:", self.timeout_spin)
        
        # Retry attempts
        self.retries_spin = QSpinBox()
        self.retries_spin.setMinimum(0)
        self.retries_spin.setMaximum(10)
        self.retries_spin.setValue(Settings.MAX_RETRIES)
        layout.addRow("Max Retry Attempts:", self.retries_spin)
        
        group.setLayout(layout)
        return group
    
    def create_ui_settings(self) -> QGroupBox:
        """Create UI settings group"""
        group = QGroupBox("🎨 User Interface")
        layout = QFormLayout()
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        layout.addRow("Theme:", self.theme_combo)
        
        # Icon cache size
        self.icon_cache_spin = QSpinBox()
        self.icon_cache_spin.setMinimum(10)
        self.icon_cache_spin.setMaximum(500)
        self.icon_cache_spin.setSuffix(" icons")
        self.icon_cache_spin.setValue(Settings.MAX_ICON_CACHE_SIZE)
        layout.addRow("Icon Cache Size:", self.icon_cache_spin)
        
        # Show notifications
        self.notifications_checkbox = QCheckBox("Show desktop notifications")
        self.notifications_checkbox.setChecked(True)
        layout.addRow("Notifications:", self.notifications_checkbox)
        
        # Confirm deletions
        self.confirm_delete_checkbox = QCheckBox("Confirm before deleting")
        self.confirm_delete_checkbox.setChecked(True)
        layout.addRow("Safety:", self.confirm_delete_checkbox)
        
        group.setLayout(layout)
        return group
    
    def create_advanced_settings(self) -> QGroupBox:
        """Create advanced settings group"""
        group = QGroupBox("🔧 Advanced")
        layout = QFormLayout()
        
        # Auto backup
        self.auto_backup_checkbox = QCheckBox(
            "Automatically backup before deployment"
        )
        self.auto_backup_checkbox.setChecked(Settings.AUTO_BACKUP_BEFORE_DEPLOY)
        layout.addRow("Backups:", self.auto_backup_checkbox)
        
        # Max backups
        self.max_backups_spin = QSpinBox()
        self.max_backups_spin.setMinimum(1)
        self.max_backups_spin.setMaximum(20)
        self.max_backups_spin.setValue(Settings.MAX_BACKUPS_PER_PROFILE)
        layout.addRow("Max Backups per Profile:", self.max_backups_spin)
        
        # Auto update check
        self.auto_update_checkbox = QCheckBox("Check for mod updates on startup")
        self.auto_update_checkbox.setChecked(Settings.ENABLE_AUTO_UPDATE)
        layout.addRow("Updates:", self.auto_update_checkbox)
        
        # Dependency auto-resolve
        self.auto_resolve_checkbox = QCheckBox(
            "Automatically resolve dependencies"
        )
        self.auto_resolve_checkbox.setChecked(Settings.ENABLE_DEPENDENCY_AUTO_RESOLVE)
        layout.addRow("Dependencies:", self.auto_resolve_checkbox)
        
        # Conflict detection
        self.conflict_detection_checkbox = QCheckBox("Enable conflict detection")
        self.conflict_detection_checkbox.setChecked(Settings.ENABLE_CONFLICT_DETECTION)
        layout.addRow("Conflicts:", self.conflict_detection_checkbox)
        
        # Log level
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText(Settings.LOG_LEVEL)
        layout.addRow("Log Level:", self.log_level_combo)
        
        # Maintenance buttons
        maintenance_widget = QWidget()
        maintenance_layout = QHBoxLayout(maintenance_widget)
        maintenance_layout.setContentsMargins(0, 0, 0, 0)
        
        clear_cache_btn = QPushButton("🗑️ Clear Cache")
        clear_cache_btn.clicked.connect(self.clear_cache)
        maintenance_layout.addWidget(clear_cache_btn)
        
        cleanup_logs_btn = QPushButton("🧹 Cleanup Old Logs")
        cleanup_logs_btn.clicked.connect(self.cleanup_logs)
        maintenance_layout.addWidget(cleanup_logs_btn)
        
        maintenance_layout.addStretch()
        
        layout.addRow("Maintenance:", maintenance_widget)
        
        group.setLayout(layout)
        return group
    
    def create_about_section(self) -> QGroupBox:
        """Create about section"""
        group = QGroupBox("ℹ️ About")
        layout = QVBoxLayout()
        
        # App info
        info_html = f"""
        <h3>{Settings.APP_NAME}</h3>
        <p><b>Version:</b> {Settings.VERSION}</p>
        <p><b>Author:</b> Your Name</p>
        <p><b>License:</b> MIT License</p>
        <br>
        <p>A modern mod manager for Valheim with smart deployment,
        dependency resolution, and profile management.</p>
        """
        
        info_label = QLabel(info_html)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Links
        links_widget = QWidget()
        links_layout = QHBoxLayout(links_widget)
        
        github_btn = QPushButton("🌐 GitHub")
        github_btn.clicked.connect(
            lambda: self.open_url("https://github.com/yourusername/valheim-mod-manager")
        )
        links_layout.addWidget(github_btn)
        
        docs_btn = QPushButton("📚 Documentation")
        docs_btn.clicked.connect(
            lambda: self.open_url("https://github.com/yourusername/valheim-mod-manager/wiki")
        )
        links_layout.addWidget(docs_btn)
        
        discord_btn = QPushButton("💬 Discord")
        discord_btn.clicked.connect(
            lambda: self.open_url("https://discord.gg/example")
        )
        links_layout.addWidget(discord_btn)
        
        links_layout.addStretch()
        
        layout.addWidget(links_widget)
        
        # Data directories
        dirs_widget = QWidget()
        dirs_layout = QVBoxLayout(dirs_widget)
        
        dirs_title = QLabel("<b>Data Directories:</b>")
        dirs_layout.addWidget(dirs_title)
        
        for name, path in [
            ("Data", Settings.DATA_DIR),
            ("Mods", Settings.MODS_DIR),
            ("Profiles", Settings.PROFILES_DIR),
            ("Logs", Settings.LOGS_DIR),
            ("Backups", Settings.BACKUPS_DIR),
        ]:
            dir_widget = QWidget()
            dir_layout = QHBoxLayout(dir_widget)
            dir_layout.setContentsMargins(0, 0, 0, 0)
            
            dir_label = QLabel(f"{name}:")
            dir_label.setMinimumWidth(80)
            dir_layout.addWidget(dir_label)
            
            dir_path = QLabel(str(path))
            dir_path.setStyleSheet("color: #888;")
            dir_layout.addWidget(dir_path)
            
            dir_layout.addStretch()
            
            open_btn = QPushButton("📂 Open")
            open_btn.clicked.connect(lambda checked, p=path: self.open_directory(p))
            dir_layout.addWidget(open_btn)
            
            dirs_layout.addWidget(dir_widget)
        
        layout.addWidget(dirs_widget)
        
        group.setLayout(layout)
        return group
    
    def load_settings(self):
        """Load settings from database"""
        try:
            # Game path
            game_path = self.db.get_setting('game_path')
            if game_path:
                self.game_path_input.setText(game_path)
            
            # Launch options
            self.console_checkbox.setChecked(
                self.db.get_setting('launch_console', 'false') == 'true'
            )
            self.skipintro_checkbox.setChecked(
                self.db.get_setting('launch_skipintro', 'false') == 'true'
            )
            self.windowed_checkbox.setChecked(
                self.db.get_setting('launch_windowed', 'false') == 'true'
            )
            self.steam_launch_checkbox.setChecked(
                self.db.get_setting('launch_via_steam', 'false') == 'true'
            )
            
            # UI settings
            theme = self.db.get_setting('theme', 'Dark')
            self.theme_combo.setCurrentText(theme)
            
            # Other settings loaded from Settings class defaults
            
        except Exception as e:
            self.logger.error(f"Failed to load settings: {e}")
    
    def save_settings(self):
        """Save settings to database"""
        try:
            # Game path
            game_path = self.game_path_input.text().strip()
            if game_path:
                # Validate
                from utils.validators import validate_game_path
                is_valid, error = validate_game_path(Path(game_path))
                if not is_valid:
                    QMessageBox.warning(self, "Invalid Game Path", error)
                    return
                
                self.db.set_setting('game_path', game_path)
            
            # Launch options
            self.db.set_setting('launch_console', 
                'true' if self.console_checkbox.isChecked() else 'false')
            self.db.set_setting('launch_skipintro',
                'true' if self.skipintro_checkbox.isChecked() else 'false')
            self.db.set_setting('launch_windowed',
                'true' if self.windowed_checkbox.isChecked() else 'false')
            self.db.set_setting('launch_via_steam',
                'true' if self.steam_launch_checkbox.isChecked() else 'false')
            
            # UI settings
            self.db.set_setting('theme', self.theme_combo.currentText())
            
            # Download settings
            self.db.set_setting('max_concurrent_downloads',
                str(self.concurrent_downloads_spin.value()))
            self.db.set_setting('cache_duration_hours',
                str(self.cache_duration_spin.value()))
            self.db.set_setting('request_timeout',
                str(self.timeout_spin.value()))
            self.db.set_setting('max_retries',
                str(self.retries_spin.value()))
            
            # Advanced settings
            self.db.set_setting('auto_backup',
                'true' if self.auto_backup_checkbox.isChecked() else 'false')
            self.db.set_setting('max_backups',
                str(self.max_backups_spin.value()))
            self.db.set_setting('auto_update',
                'true' if self.auto_update_checkbox.isChecked() else 'false')
            self.db.set_setting('auto_resolve_deps',
                'true' if self.auto_resolve_checkbox.isChecked() else 'false')
            self.db.set_setting('conflict_detection',
                'true' if self.conflict_detection_checkbox.isChecked() else 'false')
            self.db.set_setting('log_level',
                self.log_level_combo.currentText())
            
            # Emit signal
            self.settings_changed.emit()
            
            QMessageBox.information(self, "Success", "Settings saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save settings:\n{str(e)}"
            )
    
    def browse_game_path(self):
        """Browse for game directory"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Valheim Installation Directory",
            str(Path.home())
        )
        
        if path:
            self.game_path_input.setText(path)
    
    def auto_detect_game(self):
        """Auto-detect game installation"""
        try:
            game_path = self.game_launcher.find_game_path()
            
            if game_path:
                self.game_path_input.setText(str(game_path))
                QMessageBox.information(
                    self,
                    "Success",
                    f"Valheim found at:\n{game_path}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Not Found",
                    "Could not auto-detect Valheim installation.\n\n"
                    "Please browse manually."
                )
        except Exception as e:
            self.logger.error(f"Auto-detect failed: {e}")
            QMessageBox.critical(self, "Error", f"Auto-detect failed:\n{str(e)}")
    
    def clear_cache(self):
        """Clear application cache"""
        reply = QMessageBox.question(
            self,
            "Clear Cache",
            "This will clear:\n"
            "• Downloaded mod list cache\n"
            "• Icon cache\n"
            "• Temporary files\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Clear cache directory
                import shutil
                if Settings.CACHE_DIR.exists():
                    shutil.rmtree(Settings.CACHE_DIR)
                    Settings.CACHE_DIR.mkdir(parents=True)
                
                # Clear temp directory
                if Settings.TEMP_DIR.exists():
                    shutil.rmtree(Settings.TEMP_DIR)
                    Settings.TEMP_DIR.mkdir(parents=True)
                
                QMessageBox.information(self, "Success", "Cache cleared")
                
            except Exception as e:
                self.logger.error(f"Failed to clear cache: {e}")
                QMessageBox.critical(self, "Error", f"Failed:\n{str(e)}")
    
    def cleanup_logs(self):
        """Cleanup old log files"""
        reply = QMessageBox.question(
            self,
            "Cleanup Logs",
            "Remove log files older than 30 days?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                cleanup_old_logs(days=30)
                QMessageBox.information(self, "Success", "Old logs cleaned up")
            except Exception as e:
                self.logger.error(f"Failed to cleanup logs: {e}")
                QMessageBox.critical(self, "Error", f"Failed:\n{str(e)}")
    
    def open_directory(self, path: Path):
        """Open directory in file explorer"""
        import subprocess
        import platform
        
        try:
            path.mkdir(parents=True, exist_ok=True)
            
            if platform.system() == "Windows":
                subprocess.run(['explorer', str(path)])
            elif platform.system() == "Darwin":
                subprocess.run(['open', str(path)])
            else:
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            self.logger.error(f"Failed to open directory: {e}")
    
    def open_url(self, url: str):
        """Open URL in browser"""
        import webbrowser
        webbrowser.open(url)
