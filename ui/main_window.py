"""
Main Application Window with Tab Interface
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QMenuBar, QToolBar,
    QPushButton, QLabel, QComboBox, QMessageBox,
    QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QIcon
from pathlib import Path

from config.settings import Settings
from core.database import Database
from core.models import Profile
from services.thunderstore_client import ThunderstoreClient
from services.deployment_engine import DeploymentEngine
from services.dependency_resolver import DependencyResolver
from utils.logger import LoggerMixin

# Import tab widgets (will be created next)
from ui.tabs.browse_tab import BrowseTab
from ui.tabs.repository_tab import RepositoryTab
from ui.tabs.profiles_tab import ProfilesTab
from ui.tabs.configs_tab import ConfigsTab
from ui.tabs.settings_tab import SettingsTab


class MainWindow(QMainWindow, LoggerMixin):
    """Main application window"""
    
    # Signals
    profile_changed = pyqtSignal(str)  # profile_name
    status_updated = pyqtSignal(str)   # message
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.db = Database()
        self.thunderstore = ThunderstoreClient(self.db)
        self.deployment_engine = DeploymentEngine(self.db)
        self.dependency_resolver = DependencyResolver()
        
        # State
        self.current_profile: Profile = None
        self.profiles: list[Profile] = []
        
        # Setup UI
        self.setup_ui()
        self.load_profiles()
        
        # Connect signals
        self.connect_signals()
        
        self.logger.info("Main window initialized")
    
    def setup_ui(self):
        """Setup user interface"""
        self.setWindowTitle(f"{Settings.APP_NAME} v{Settings.VERSION}")
        self.resize(Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top toolbar
        toolbar_widget = self.create_toolbar()
        main_layout.addWidget(toolbar_widget)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.browse_tab = BrowseTab(self.thunderstore, self.db)
        self.repository_tab = RepositoryTab(self.db)
        self.profiles_tab = ProfilesTab(self.db, self.deployment_engine)
        self.configs_tab = ConfigsTab(self.db)
        self.settings_tab = SettingsTab(self.db)
        
        self.tab_widget.addTab(self.browse_tab, "Browse Mods")
        self.tab_widget.addTab(self.repository_tab, "Repository")
        self.tab_widget.addTab(self.profiles_tab, "Profiles")
        self.tab_widget.addTab(self.configs_tab, "Configs")
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        # Status bar
        self.setup_status_bar()
        
        # Menu bar
        self.setup_menu_bar()
    
    def create_toolbar(self) -> QWidget:
        """Create top toolbar with profile selector and launch button"""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Profile selector
        profile_label = QLabel("Profile:")
        layout.addWidget(profile_label)
        
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)
        layout.addWidget(self.profile_combo)
        
        layout.addStretch()
        
        # Action buttons
        self.launch_btn = QPushButton("🚀 Launch Game")
        self.launch_btn.setMinimumWidth(120)
        self.launch_btn.clicked.connect(self.launch_game)
        layout.addWidget(self.launch_btn)
        
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.clicked.connect(lambda: self.tab_widget.setCurrentWidget(self.settings_tab))
        layout.addWidget(settings_btn)
        
        return toolbar
    
    def setup_status_bar(self):
        """Setup status bar with info labels"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status message
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        self.status_bar.addPermanentWidget(QLabel(" | "))
        
        # Mod count
        self.mod_count_label = QLabel("Mods: 0")
        self.status_bar.addPermanentWidget(self.mod_count_label)
        
        self.status_bar.addPermanentWidget(QLabel(" | "))
        
        # Profile count
        self.profile_count_label = QLabel("Profiles: 0")
        self.status_bar.addPermanentWidget(self.profile_count_label)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def setup_menu_bar(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        import_action = QAction("Import Profile...", self)
        import_action.triggered.connect(self.import_profile)
        file_menu.addAction(import_action)
        
        export_action = QAction("Export Profile...", self)
        export_action.triggered.connect(self.export_profile)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        refresh_action = QAction("Refresh Mod List", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_mod_list)
        tools_menu.addAction(refresh_action)
        
        check_updates_action = QAction("Check for Updates", self)
        check_updates_action.triggered.connect(self.check_for_updates)
        tools_menu.addAction(check_updates_action)
        
        tools_menu.addSeparator()
        
        clear_cache_action = QAction("Clear Cache", self)
        clear_cache_action.triggered.connect(self.clear_cache)
        tools_menu.addAction(clear_cache_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        logs_action = QAction("View Logs", self)
        logs_action.triggered.connect(self.view_logs)
        help_menu.addAction(logs_action)
    
    def connect_signals(self):
        """Connect internal signals"""
        self.status_updated.connect(self.update_status_message)
        
        # Connect tab signals
        self.profiles_tab.profile_created.connect(self.on_profile_created)
        self.profiles_tab.profile_deleted.connect(self.on_profile_deleted)
        self.profiles_tab.profile_activated.connect(self.on_profile_activated)
        
        self.repository_tab.mod_installed.connect(self.update_mod_count)
        self.repository_tab.mod_deleted.connect(self.update_mod_count)
    
    def load_profiles(self):
        """Load profiles from storage"""
        try:
            # Load profiles from JSON files in profiles directory
            profiles_dir = Settings.PROFILES_DIR
            profiles_dir.mkdir(parents=True, exist_ok=True)
            
            self.profiles.clear()
            self.profile_combo.clear()
            
            for profile_file in profiles_dir.glob("*.json"):
                try:
                    profile = Profile.import_from_json(profile_file)
                    self.profiles.append(profile)
                    self.profile_combo.addItem(profile.name)
                except Exception as e:
                    self.logger.error(f"Failed to load profile {profile_file}: {e}")
            
            # Update counts
            self.profile_count_label.setText(f"Profiles: {len(self.profiles)}")
            
            # Select last active profile
            last_profile = self.db.get_setting('last_profile')
            if last_profile and last_profile in [p.name for p in self.profiles]:
                self.profile_combo.setCurrentText(last_profile)
            elif self.profiles:
                self.profile_combo.setCurrentIndex(0)
            
        except Exception as e:
            self.logger.error(f"Failed to load profiles: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load profiles: {e}")
    
    def on_profile_changed(self, profile_name: str):
        """Handle profile selection change"""
        if not profile_name:
            self.current_profile = None
            return
        
        # Find profile
        for profile in self.profiles:
            if profile.name == profile_name:
                self.current_profile = profile
                self.db.set_setting('last_profile', profile_name)
                self.profile_changed.emit(profile_name)
                
                # Update tabs
                self.profiles_tab.set_current_profile(profile)
                self.configs_tab.set_current_profile(profile)
                
                break
    
    def launch_game(self):
        """Launch game with current profile"""
        if not self.current_profile:
            QMessageBox.warning(self, "No Profile", "Please select a profile first")
            return
        
        # Validate game path
        if not self.current_profile.game_path:
            QMessageBox.warning(
                self,
                "No Game Path",
                "Please set game path in profile settings"
            )
            return
        
        try:
            # Deploy profile
            self.status_updated.emit("Deploying mods...")
            self.progress_bar.setVisible(True)
            
            def progress_callback(current, total, message):
                self.progress_bar.setMaximum(total)
                self.progress_bar.setValue(current)
                self.status_updated.emit(message)
            
            self.deployment_engine.deploy_profile(
                self.current_profile,
                progress_callback
            )
            
            self.progress_bar.setVisible(False)
            
            # Launch game
            from services.game_launcher import GameLauncher
            launcher = GameLauncher()
            
            if launcher.launch_game(self.current_profile.game_path):
                self.status_updated.emit("Game launched successfully")
                
                # Log usage
                for mod in self.current_profile.get_enabled_mods():
                    self.db.log_usage(mod.id, self.current_profile.name)
            else:
                QMessageBox.warning(self, "Launch Failed", "Failed to launch game")
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.logger.error(f"Failed to launch game: {e}")
            QMessageBox.critical(
                self,
                "Launch Error",
                f"Failed to launch game:\n{str(e)}"
            )
    
    def refresh_mod_list(self):
        """Refresh mod list from Thunderstore"""
        try:
            self.status_updated.emit("Refreshing mod list...")
            self.thunderstore.clear_cache()
            self.browse_tab.refresh()
            self.status_updated.emit("Mod list refreshed")
        except Exception as e:
            self.logger.error(f"Failed to refresh: {e}")
            QMessageBox.warning(self, "Error", f"Failed to refresh: {e}")
    
    def check_for_updates(self):
        """Check for mod updates"""
        try:
            installed_mods = {
                m.id: m.version
                for m in self.db.get_all_mods(installed_only=True)
            }
            
            updates = self.thunderstore.check_for_updates(installed_mods)
            
            if updates:
                message = f"Found {len(updates)} update(s):\n\n"
                for update in updates[:10]:  # Show first 10
                    message += (
                        f"• {update['mod_id']}: "
                        f"{update['current_version']} → {update['latest_version']}\n"
                    )
                
                if len(updates) > 10:
                    message += f"\n...and {len(updates) - 10} more"
                
                QMessageBox.information(self, "Updates Available", message)
            else:
                QMessageBox.information(
                    self,
                    "No Updates",
                    "All mods are up to date!"
                )
                
        except Exception as e:
            self.logger.error(f"Update check failed: {e}")
            QMessageBox.warning(self, "Error", f"Update check failed: {e}")
    
    def clear_cache(self):
        """Clear application cache"""
        reply = QMessageBox.question(
            self,
            "Clear Cache",
            "This will clear cached mod data. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.thunderstore.clear_cache()
            QMessageBox.information(self, "Success", "Cache cleared")
    
    def import_profile(self):
        """Import profile from file"""
        from PyQt6.QtWidgets import QFileDialog
        
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
                QMessageBox.information(
                    self,
                    "Success",
                    f"Profile '{profile.name}' imported successfully"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Import Failed",
                    f"Failed to import profile:\n{str(e)}"
                )
    
    def export_profile(self):
        """Export current profile to file"""
        if not self.current_profile:
            QMessageBox.warning(self, "No Profile", "Please select a profile first")
            return
        
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profile",
            str(Settings.PROFILES_DIR / f"{self.current_profile.name}.json"),
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                self.current_profile.export_to_json(Path(file_path))
                QMessageBox.information(
                    self,
                    "Success",
                    f"Profile exported to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export profile:\n{str(e)}"
                )
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""
        <h2>{Settings.APP_NAME}</h2>
        <p>Version {Settings.VERSION}</p>
        <p>A modern mod manager for Valheim</p>
        <br>
        <p>Features:</p>
        <ul>
        <li>Browse and download mods from Thunderstore</li>
        <li>Smart deployment with hash-based change detection</li>
        <li>Profile management for different mod configurations</li>
        <li>Automatic dependency resolution</li>
        <li>Configuration management</li>
        </ul>
        """
        QMessageBox.about(self, "About", about_text)
    
    def view_logs(self):
        """View application logs"""
        log_file = Settings.LOGS_DIR / "valheim_mod_manager.log"
        
        if not log_file.exists():
            QMessageBox.information(self, "No Logs", "No log file found")
            return
        
        # Show logs in dialog
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Application Logs")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setPlainText(log_file.read_text(encoding='utf-8'))
        layout.addWidget(log_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    def update_status_message(self, message: str):
        """Update status bar message"""
        self.status_label.setText(message)
    
    def update_mod_count(self):
        """Update mod count in status bar"""
        count = len(self.db.get_all_mods(installed_only=True))
        self.mod_count_label.setText(f"Mods: {count}")
    
    def on_profile_created(self, profile_name: str):
        """Handle profile creation"""
        self.load_profiles()
        self.profile_combo.setCurrentText(profile_name)
    
    def on_profile_deleted(self, profile_name: str):
        """Handle profile deletion"""
        self.load_profiles()
    
    def on_profile_activated(self, profile_name: str):
        """Handle profile activation"""
        self.profile_combo.setCurrentText(profile_name)
    
    def closeEvent(self, event):
        """Handle window close"""
        reply = QMessageBox.question(
            self,
            "Exit",
            "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.logger.info("Application closing")
            event.accept()
        else:
            event.ignore()
