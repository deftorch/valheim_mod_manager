"""
Configs Tab - Edit Mod Configuration Files
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
    QComboBox, QTextEdit, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter
from pathlib import Path
import re

from core.database import Database
from core.models import Profile, ModConfig
from services.config_manager import ConfigManager
from utils.logger import LoggerMixin
from config.settings import Settings


class ConfigSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for config files"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Define highlighting rules
        self.highlighting_rules = []
        
        # Section headers [Section]
        section_format = QTextCharFormat()
        section_format.setForeground(QColor("#569CD6"))  # Blue
        section_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            r'\[[\w\s]+\]',
            section_format
        ))
        
        # Keys
        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#9CDCFE"))  # Light blue
        self.highlighting_rules.append((
            r'^\s*[\w.]+(?=\s*=)',
            key_format
        ))
        
        # Values
        value_format = QTextCharFormat()
        value_format.setForeground(QColor("#CE9178"))  # Orange
        self.highlighting_rules.append((
            r'=\s*([^#\n]+)',
            value_format
        ))
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))  # Green
        self.highlighting_rules.append((
            r'#[^\n]*',
            comment_format
        ))
        
        # Boolean values
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#4EC9B0"))  # Cyan
        bool_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            r'\b(true|false|True|False|TRUE|FALSE)\b',
            bool_format
        ))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))  # Light green
        self.highlighting_rules.append((
            r'\b\d+\.?\d*\b',
            number_format
        ))
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to text block"""
        for pattern, fmt in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class ConfigsTab(QWidget, LoggerMixin):
    """Configuration file editor"""
    
    config_saved = pyqtSignal(str, str)  # mod_id, profile_name
    
    def __init__(self, database: Database):
        super().__init__()
        self.db = database
        self.config_manager = ConfigManager(self.db)
        
        self.current_profile = None
        self.current_mod = None
        self.current_config = None
        self.is_modified = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Header with selectors
        header = self.create_header()
        layout.addWidget(header)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Config files list
        left_panel = self.create_config_list()
        splitter.addWidget(left_panel)
        
        # Right panel - Editor
        right_panel = self.create_editor_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)
        
        # Status bar
        status_widget = self.create_status_bar()
        layout.addWidget(status_widget)
    
    def create_header(self) -> QWidget:
        """Create header with profile and mod selectors"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Profile selector
        profile_label = QLabel("Profile:")
        layout.addWidget(profile_label)
        
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(150)
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)
        layout.addWidget(self.profile_combo)
        
        layout.addSpacing(20)
        
        # Mod selector
        mod_label = QLabel("Mod:")
        layout.addWidget(mod_label)
        
        self.mod_combo = QComboBox()
        self.mod_combo.setMinimumWidth(200)
        self.mod_combo.currentTextChanged.connect(self.on_mod_changed)
        layout.addWidget(self.mod_combo)
        
        layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_lists)
        layout.addWidget(refresh_btn)
        
        return widget
    
    def create_config_list(self) -> QWidget:
        """Create config files list"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("<h3>Configuration Files</h3>")
        layout.addWidget(title)
        
        # Custom/Default toggle
        toggle_widget = QWidget()
        toggle_layout = QHBoxLayout(toggle_widget)
        
        self.show_default_checkbox = QCheckBox("Show Default")
        self.show_default_checkbox.setChecked(True)
        self.show_default_checkbox.stateChanged.connect(self.refresh_config_list)
        toggle_layout.addWidget(self.show_default_checkbox)
        
        self.show_custom_checkbox = QCheckBox("Show Custom")
        self.show_custom_checkbox.setChecked(True)
        self.show_custom_checkbox.stateChanged.connect(self.refresh_config_list)
        toggle_layout.addWidget(self.show_custom_checkbox)
        
        layout.addWidget(toggle_widget)
        
        # List widget
        self.config_list = QListWidget()
        self.config_list.currentItemChanged.connect(self.on_config_selected)
        layout.addWidget(self.config_list)
        
        # Info label
        self.info_label = QLabel("Select a mod to view configs")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #888; padding: 10px;")
        layout.addWidget(self.info_label)
        
        return widget
    
    def create_editor_panel(self) -> QWidget:
        """Create configuration editor panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        
        self.editor_title = QLabel("<h3>No config selected</h3>")
        header_layout.addWidget(self.editor_title)
        
        header_layout.addStretch()
        
        self.custom_indicator = QLabel()
        header_layout.addWidget(self.custom_indicator)
        
        layout.addWidget(header_widget)
        
        # Editor
        self.editor = QTextEdit()
        self.editor.setFontFamily("Consolas, Monaco, monospace")
        self.editor.setTabStopDistance(40)
        self.editor.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.editor)
        
        # Apply syntax highlighting
        self.highlighter = ConfigSyntaxHighlighter(self.editor.document())
        
        # Action buttons
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_config)
        buttons_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton("🔄 Reset to Default")
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self.reset_to_default)
        buttons_layout.addWidget(self.reset_btn)
        
        buttons_layout.addStretch()
        
        self.validate_btn = QPushButton("✅ Validate")
        self.validate_btn.setEnabled(False)
        self.validate_btn.clicked.connect(self.validate_config)
        buttons_layout.addWidget(self.validate_btn)
        
        layout.addWidget(buttons_widget)
        
        return widget
    
    def create_status_bar(self) -> QWidget:
        """Create status bar"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.line_col_label = QLabel("Line: 1, Col: 1")
        layout.addWidget(self.line_col_label)
        
        return widget
    
    def refresh_lists(self):
        """Refresh profile and mod lists"""
        # Load profiles
        self.profile_combo.clear()
        profiles_dir = Settings.PROFILES_DIR
        
        if profiles_dir.exists():
            for profile_file in profiles_dir.glob("*.json"):
                try:
                    profile = Profile.import_from_json(profile_file)
                    self.profile_combo.addItem(profile.name)
                except:
                    pass
    
    def on_profile_changed(self, profile_name: str):
        """Handle profile selection change"""
        if not profile_name:
            return
        
        try:
            # Load profile
            profile_file = Settings.PROFILES_DIR / f"{profile_name}.json"
            if profile_file.exists():
                self.current_profile = Profile.import_from_json(profile_file)
                
                # Update mod list
                self.mod_combo.clear()
                for mod in self.current_profile.mods:
                    self.mod_combo.addItem(mod.name, mod.id)
        except Exception as e:
            self.logger.error(f"Failed to load profile: {e}")
    
    def on_mod_changed(self, mod_name: str):
        """Handle mod selection change"""
        if not mod_name:
            return
        
        mod_id = self.mod_combo.currentData()
        if not mod_id:
            return
        
        # Find mod
        self.current_mod = None
        if self.current_profile:
            self.current_mod = self.current_profile.get_mod(mod_id)
        
        # Refresh config list
        self.refresh_config_list()
    
    def refresh_config_list(self):
        """Refresh configuration files list"""
        self.config_list.clear()
        
        if not self.current_mod:
            self.info_label.setText("Select a mod to view configs")
            return
        
        if not self.current_mod.config_files:
            self.info_label.setText("This mod has no configuration files")
            return
        
        # Show configs
        show_default = self.show_default_checkbox.isChecked()
        show_custom = self.show_custom_checkbox.isChecked()
        
        for config_name in self.current_mod.config_files:
            # Check if custom config exists
            has_custom = self.config_manager.load_config(
                self.current_mod.id,
                self.current_profile.name if self.current_profile else "default"
            ) is not None
            
            if (show_default and not has_custom) or (show_custom and has_custom):
                item = QListWidgetItem()
                
                icon = "📝" if has_custom else "📄"
                item.setText(f"{icon} {config_name}")
                item.setData(Qt.ItemDataRole.UserRole, config_name)
                
                self.config_list.addItem(item)
        
        self.info_label.setText(
            f"{self.config_list.count()} config file(s) available"
        )
    
    def on_config_selected(self, current, previous):
        """Handle config file selection"""
        if not current or not self.current_mod or not self.current_profile:
            return
        
        # Check if current config is modified
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Save before switching?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                # Revert selection
                if previous:
                    self.config_list.setCurrentItem(previous)
                return
            elif reply == QMessageBox.StandardButton.Yes:
                self.save_config()
        
        config_name = current.data(Qt.ItemDataRole.UserRole)
        self.load_config(config_name)
    
    def load_config(self, config_name: str):
        """Load configuration file"""
        try:
            self.current_config = self.config_manager.load_config(
                self.current_mod.id,
                self.current_profile.name
            )
            
            if not self.current_config:
                # No config found
                self.editor_title.setText(f"<h3>{config_name}</h3>")
                self.editor.setPlainText("# No configuration found")
                self.editor.setReadOnly(True)
                return
            
            # Update UI
            self.editor_title.setText(f"<h3>{config_name}</h3>")
            
            if self.current_config.is_custom:
                self.custom_indicator.setText("🔧 Custom")
                self.custom_indicator.setStyleSheet("color: #4CAF50; font-weight: bold;")
            else:
                self.custom_indicator.setText("📄 Default")
                self.custom_indicator.setStyleSheet("color: #888;")
            
            # Load content
            self.editor.setReadOnly(False)
            self.editor.setPlainText(self.current_config.content)
            self.is_modified = False
            
            # Enable buttons
            self.save_btn.setEnabled(False)
            self.reset_btn.setEnabled(self.current_config.is_custom)
            self.validate_btn.setEnabled(True)
            
            self.status_label.setText("Config loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load config:\n{str(e)}"
            )
    
    def on_text_changed(self):
        """Handle text change in editor"""
        if self.current_config and not self.is_modified:
            self.is_modified = True
            self.save_btn.setEnabled(True)
            self.status_label.setText("Modified")
    
    def save_config(self):
        """Save current configuration"""
        if not self.current_config:
            return
        
        try:
            # Update content
            self.current_config.content = self.editor.toPlainText()
            self.current_config.is_custom = True
            
            # Save
            self.config_manager.save_config(self.current_config)
            
            self.is_modified = False
            self.save_btn.setEnabled(False)
            self.reset_btn.setEnabled(True)
            
            self.status_label.setText("Config saved")
            
            # Update indicator
            self.custom_indicator.setText("🔧 Custom")
            self.custom_indicator.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            # Emit signal
            self.config_saved.emit(self.current_mod.id, self.current_profile.name)
            
            QMessageBox.information(self, "Success", "Configuration saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save config:\n{str(e)}"
            )
    
    def reset_to_default(self):
        """Reset config to default"""
        if not self.current_config:
            return
        
        reply = QMessageBox.question(
            self,
            "Reset to Default",
            "Are you sure you want to reset this config to default?\n\n"
            "This will discard your custom changes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Reset
                success = self.config_manager.reset_to_default(
                    self.current_mod.id,
                    self.current_profile.name
                )
                
                if success:
                    # Reload config
                    self.refresh_config_list()
                    
                    # Find and select the config again
                    for i in range(self.config_list.count()):
                        item = self.config_list.item(i)
                        if item.data(Qt.ItemDataRole.UserRole) == self.current_config.config_name:
                            self.config_list.setCurrentItem(item)
                            break
                    
                    self.status_label.setText("Reset to default")
                    QMessageBox.information(self, "Success", "Config reset to default")
                
            except Exception as e:
                self.logger.error(f"Failed to reset config: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to reset:\n{str(e)}"
                )
    
    def validate_config(self):
        """Validate current configuration"""
        if not self.current_config:
            return
        
        try:
            # Update content from editor
            self.current_config.content = self.editor.toPlainText()
            
            # Validate
            is_valid, errors = self.config_manager.validate_config(self.current_config)
            
            if is_valid:
                QMessageBox.information(
                    self,
                    "Validation",
                    "✅ Configuration is valid!"
                )
            else:
                error_msg = "❌ Configuration has errors:\n\n"
                error_msg += "\n".join(f"• {err}" for err in errors)
                QMessageBox.warning(self, "Validation Errors", error_msg)
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Validation failed:\n{str(e)}"
            )
    
    def set_current_profile(self, profile: Profile):
        """Set current profile externally"""
        self.current_profile = profile
        
        # Find and select in combo
        index = self.profile_combo.findText(profile.name)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)
