"""
Repository Tab - Manage Downloaded Mods
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
    QTextEdit, QTabWidget, QMessageBox, QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from pathlib import Path
import markdown

from core.database import Database
from core.models import Mod
from utils.logger import LoggerMixin
from config.settings import Settings


class RepositoryTab(QWidget, LoggerMixin):
    """Manage downloaded mods in repository"""
    
    mod_installed = pyqtSignal()
    mod_deleted = pyqtSignal()
    mod_updated = pyqtSignal(str)  # mod_id
    
    def __init__(self, database: Database):
        super().__init__()
        self.db = database
        self.current_mods = []
        self.selected_mod = None
        
        self.setup_ui()
        self.load_mods()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Header with count and actions
        header = self.create_header()
        layout.addWidget(header)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Mod list
        left_panel = self.create_mod_list()
        splitter.addWidget(left_panel)
        
        # Right panel - Mod details
        right_panel = self.create_details_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)
    
    def create_header(self) -> QWidget:
        """Create header with count and actions"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.count_label = QLabel("Installed Mods: 0")
        self.count_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.count_label)
        
        layout.addStretch()
        
        # Action buttons
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_mods)
        layout.addWidget(refresh_btn)
        
        update_all_btn = QPushButton("⬆️ Update All")
        update_all_btn.clicked.connect(self.update_all_mods)
        layout.addWidget(update_all_btn)
        
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.clicked.connect(self.delete_selected_mod)
        layout.addWidget(delete_btn)
        
        return widget
    
    def create_mod_list(self) -> QWidget:
        """Create mod list widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Filter/Sort options
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        
        filter_label = QLabel("Filter:")
        filter_layout.addWidget(filter_label)
        
        # TODO: Add filter combo boxes
        
        filter_layout.addStretch()
        layout.addWidget(filter_widget)
        
        # List widget
        self.mod_list = QListWidget()
        self.mod_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.mod_list.customContextMenuRequested.connect(self.show_context_menu)
        self.mod_list.currentItemChanged.connect(self.on_mod_selected)
        layout.addWidget(self.mod_list)
        
        return widget
    
    def create_details_panel(self) -> QWidget:
        """Create details panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Mod info header
        self.info_label = QLabel("<h2>Select a mod to view details</h2>")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Tab widget for different sections
        self.details_tabs = QTabWidget()
        
        # Info tab
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.details_tabs.addTab(self.info_text, "📋 Info")
        
        # README tab
        self.readme_view = QTextEdit()
        self.readme_view.setReadOnly(True)
        self.details_tabs.addTab(self.readme_view, "📖 README")
        
        # Changelog tab
        self.changelog_view = QTextEdit()
        self.changelog_view.setReadOnly(True)
        self.details_tabs.addTab(self.changelog_view, "📝 Changelog")
        
        # Files tab
        self.files_list = QListWidget()
        self.details_tabs.addTab(self.files_list, "📁 Files")
        
        # Dependencies tab
        self.deps_list = QListWidget()
        self.details_tabs.addTab(self.deps_list, "🔗 Dependencies")
        
        layout.addWidget(self.details_tabs)
        
        # Action buttons
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        
        self.open_folder_btn = QPushButton("📂 Open Folder")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self.open_mod_folder)
        buttons_layout.addWidget(self.open_folder_btn)
        
        self.edit_config_btn = QPushButton("⚙️ Edit Config")
        self.edit_config_btn.setEnabled(False)
        self.edit_config_btn.clicked.connect(self.edit_mod_config)
        buttons_layout.addWidget(self.edit_config_btn)
        
        buttons_layout.addStretch()
        
        self.update_btn = QPushButton("⬆️ Update")
        self.update_btn.setEnabled(False)
        self.update_btn.clicked.connect(self.update_selected_mod)
        buttons_layout.addWidget(self.update_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected_mod)
        buttons_layout.addWidget(self.delete_btn)
        
        layout.addWidget(buttons_widget)
        
        return widget
    
    def load_mods(self):
        """Load installed mods from database"""
        try:
            self.logger.info("Loading installed mods")
            
            # Get all installed mods
            self.current_mods = self.db.get_all_mods(installed_only=True)
            
            # Update list
            self.mod_list.clear()
            
            for mod in self.current_mods:
                item = QListWidgetItem()
                
                # Set text
                text = f"🎨 {mod.name}\n"
                text += f"   v{mod.version} by {mod.author}\n"
                
                if mod.update_available:
                    text += "   ⬆️ Update available"
                
                item.setText(text)
                item.setData(Qt.ItemDataRole.UserRole, mod)
                
                self.mod_list.addItem(item)
            
            # Update count
            self.count_label.setText(f"Installed Mods: {len(self.current_mods)}")
            
            self.logger.info(f"Loaded {len(self.current_mods)} mods")
            
        except Exception as e:
            self.logger.error(f"Failed to load mods: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load mods:\n{str(e)}")
    
    def on_mod_selected(self, current, previous):
        """Handle mod selection"""
        if not current:
            return
        
        mod = current.data(Qt.ItemDataRole.UserRole)
        self.selected_mod = mod
        
        # Update details
        self.update_details(mod)
        
        # Enable buttons
        self.open_folder_btn.setEnabled(True)
        self.edit_config_btn.setEnabled(len(mod.config_files) > 0)
        self.update_btn.setEnabled(mod.update_available)
        self.delete_btn.setEnabled(True)
    
    def update_details(self, mod: Mod):
        """Update details panel"""
        # Update header
        self.info_label.setText(
            f"<h2>{mod.name}</h2>"
            f"<p>by {mod.author} • v{mod.version}</p>"
        )
        
        # Info tab
        info_html = f"""
        <h3>Information</h3>
        <table>
        <tr><td><b>ID:</b></td><td>{mod.id}</td></tr>
        <tr><td><b>Version:</b></td><td>{mod.version}</td></tr>
        <tr><td><b>Author:</b></td><td>{mod.author}</td></tr>
        <tr><td><b>Rating:</b></td><td>{'⭐' * int(mod.rating)} {mod.rating:.1f}</td></tr>
        <tr><td><b>Downloads:</b></td><td>{mod.downloads:,}</td></tr>
        <tr><td><b>Installed:</b></td><td>{mod.downloaded_at.strftime('%Y-%m-%d %H:%M') if mod.downloaded_at else 'Unknown'}</td></tr>
        </table>
        <h3>Description</h3>
        <p>{mod.description}</p>
        """
        
        if mod.full_description:
            info_html += f"<h3>Full Description</h3><p>{mod.full_description}</p>"
        
        self.info_text.setHtml(info_html)
        
        # README tab
        readme_content = mod.get_readme_content()
        try:
            readme_html = markdown.markdown(readme_content)
            self.readme_view.setHtml(readme_html)
        except:
            self.readme_view.setPlainText(readme_content)
        
        # Changelog tab
        changelog_content = mod.get_changelog_content()
        try:
            changelog_html = markdown.markdown(changelog_content)
            self.changelog_view.setHtml(changelog_html)
        except:
            self.changelog_view.setPlainText(changelog_content)
        
        # Files tab
        self.files_list.clear()
        files = mod.get_file_list()
        for file_path in files:
            try:
                rel_path = file_path.relative_to(mod.install_path)
                size = file_path.stat().st_size
                size_str = self.format_size(size)
                item = QListWidgetItem(f"📄 {rel_path} ({size_str})")
                self.files_list.addItem(item)
            except:
                pass
        
        if not files:
            self.files_list.addItem(QListWidgetItem("No files found"))
        
        # Dependencies tab
        self.deps_list.clear()
        if mod.dependencies:
            for dep in mod.dependencies:
                constraint = dep.version_constraint if dep.version_constraint != "*" else "any version"
                item = QListWidgetItem(f"🔗 {dep.mod_id} ({constraint})")
                self.deps_list.addItem(item)
        else:
            self.deps_list.addItem(QListWidgetItem("No dependencies"))
    
    def show_context_menu(self, position):
        """Show context menu for mod list"""
        item = self.mod_list.itemAt(position)
        if not item:
            return
        
        mod = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu()
        
        # Open folder action
        open_action = QAction("📂 Open Folder", self)
        open_action.triggered.connect(self.open_mod_folder)
        menu.addAction(open_action)
        
        # Edit config action
        if mod.config_files:
            config_action = QAction("⚙️ Edit Config", self)
            config_action.triggered.connect(self.edit_mod_config)
            menu.addAction(config_action)
        
        menu.addSeparator()
        
        # Update action
        if mod.update_available:
            update_action = QAction("⬆️ Update", self)
            update_action.triggered.connect(self.update_selected_mod)
            menu.addAction(update_action)
        
        # Delete action
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(self.delete_selected_mod)
        menu.addAction(delete_action)
        
        menu.exec(self.mod_list.mapToGlobal(position))
    
    def open_mod_folder(self):
        """Open mod folder in file explorer"""
        if not self.selected_mod or not self.selected_mod.install_path:
            return
        
        import subprocess
        import platform
        
        path = self.selected_mod.install_path
        
        try:
            if platform.system() == "Windows":
                subprocess.run(['explorer', str(path)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['open', str(path)])
            else:  # Linux
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            self.logger.error(f"Failed to open folder: {e}")
            QMessageBox.warning(self, "Error", f"Failed to open folder:\n{str(e)}")
    
    def edit_mod_config(self):
        """Open config editor for mod"""
        if not self.selected_mod:
            return
        
        # TODO: Open config editor dialog
        QMessageBox.information(
            self,
            "Config Editor",
            "Config editor will be opened here"
        )
    
    def update_selected_mod(self):
        """Update selected mod"""
        if not self.selected_mod:
            return
        
        reply = QMessageBox.question(
            self,
            "Update Mod",
            f"Update {self.selected_mod.name} to latest version?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implement mod update
            QMessageBox.information(self, "Update", "Mod update not yet implemented")
    
    def delete_selected_mod(self):
        """Delete selected mod"""
        if not self.selected_mod:
            return
        
        reply = QMessageBox.question(
            self,
            "Delete Mod",
            f"Are you sure you want to delete {self.selected_mod.name}?\n\n"
            f"This will remove the mod from your repository.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Delete from database
                self.db.delete_mod(self.selected_mod.id)
                
                # Delete files
                if self.selected_mod.install_path and self.selected_mod.install_path.exists():
                    import shutil
                    shutil.rmtree(self.selected_mod.install_path)
                
                self.logger.info(f"Deleted mod: {self.selected_mod.id}")
                
                # Reload list
                self.load_mods()
                
                # Emit signal
                self.mod_deleted.emit()
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Mod '{self.selected_mod.name}' deleted successfully"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to delete mod: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete mod:\n{str(e)}"
                )
    
    def update_all_mods(self):
        """Update all mods that have updates available"""
        updates = [m for m in self.current_mods if m.update_available]
        
        if not updates:
            QMessageBox.information(
                self,
                "No Updates",
                "All mods are up to date!"
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Update All",
            f"Found {len(updates)} mod(s) with updates available.\n\n"
            f"Update all mods?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implement batch update
            QMessageBox.information(self, "Update", "Batch update not yet implemented")
    
    def format_size(self, bytes_size: int) -> str:
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
