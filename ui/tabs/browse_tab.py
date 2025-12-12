"""
Browse Mods Tab - Search and Download from Thunderstore
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLineEdit, QComboBox, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QTextEdit, QMessageBox,
    QProgressBar, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QPixmap
from pathlib import Path

from services.thunderstore_client import ThunderstoreClient
from core.database import Database
from core.models import Mod, ModDependency
from utils.logger import LoggerMixin
from config.settings import Settings


class DownloadWorker(QThread):
    """Worker thread for downloading mods"""
    
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, client: ThunderstoreClient, mod_data: dict):
        super().__init__()
        self.client = client
        self.mod_data = mod_data
    
    def run(self):
        """Download mod in background"""
        try:
            # Download mod
            download_path = self.client.download_mod(
                self.mod_data,
                Settings.TEMP_DIR,
                progress_callback=self.progress.emit
            )
            
            self.finished.emit(True, str(download_path))
            
        except Exception as e:
            self.finished.emit(False, str(e))


class BrowseTab(QWidget, LoggerMixin):
    """Browse and download mods from Thunderstore"""
    
    mod_downloaded = pyqtSignal(str)  # mod_id
    
    def __init__(self, thunderstore: ThunderstoreClient, database: Database):
        super().__init__()
        self.thunderstore = thunderstore
        self.db = database
        
        self.current_mods = []
        self.selected_mod = None
        self.download_worker = None
        
        self.setup_ui()
        self.load_mods()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Search and filter bar
        search_bar = self.create_search_bar()
        layout.addWidget(search_bar)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Mod list
        left_panel = self.create_mod_list()
        splitter.addWidget(left_panel)
        
        # Right panel - Mod details
        right_panel = self.create_details_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([400, 600])
        layout.addWidget(splitter)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def create_search_bar(self) -> QWidget:
        """Create search and filter bar"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search mods...")
        self.search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_input)
        
        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        self.category_combo.currentTextChanged.connect(self.apply_filters)
        layout.addWidget(self.category_combo)
        
        # Sort by
        sort_label = QLabel("Sort:")
        layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Downloads", "Rating", "Name", "Updated"])
        self.sort_combo.currentTextChanged.connect(self.apply_filters)
        layout.addWidget(self.sort_combo)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)
        
        return widget
    
    def create_mod_list(self) -> QWidget:
        """Create mod list widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Count label
        self.count_label = QLabel("Mods: 0")
        layout.addWidget(self.count_label)
        
        # List widget
        self.mod_list = QListWidget()
        self.mod_list.currentItemChanged.connect(self.on_mod_selected)
        layout.addWidget(self.mod_list)
        
        return widget
    
    def create_details_panel(self) -> QWidget:
        """Create mod details panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with icon and basic info
        header = QWidget()
        header_layout = QHBoxLayout(header)
        
        self.mod_icon = QLabel()
        self.mod_icon.setFixedSize(128, 128)
        self.mod_icon.setScaledContents(True)
        header_layout.addWidget(self.mod_icon)
        
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        self.mod_name_label = QLabel("<b>Select a mod</b>")
        self.mod_name_label.setWordWrap(True)
        info_layout.addWidget(self.mod_name_label)
        
        self.mod_author_label = QLabel("")
        info_layout.addWidget(self.mod_author_label)
        
        self.mod_version_label = QLabel("")
        info_layout.addWidget(self.mod_version_label)
        
        self.mod_stats_label = QLabel("")
        info_layout.addWidget(self.mod_stats_label)
        
        info_layout.addStretch()
        header_layout.addWidget(info_widget)
        
        layout.addWidget(header)
        
        # Tab widget for different info sections
        self.details_tabs = QTabWidget()
        
        # Description tab
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.details_tabs.addTab(self.description_text, "Description")
        
        # Dependencies tab
        self.dependencies_list = QListWidget()
        self.details_tabs.addTab(self.dependencies_list, "Dependencies")
        
        layout.addWidget(self.details_tabs)
        
        # Download button
        self.download_btn = QPushButton("📥 Download")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.download_mod)
        layout.addWidget(self.download_btn)
        
        return widget
    
    def load_mods(self):
        """Load mods from Thunderstore"""
        try:
            self.logger.info("Loading mods from Thunderstore")
            
            # Fetch mods
            mods = self.thunderstore.fetch_mods()
            self.current_mods = mods
            
            # Load categories
            categories = self.thunderstore.get_categories()
            self.category_combo.clear()
            self.category_combo.addItem("All Categories")
            self.category_combo.addItems(categories)
            
            # Display mods
            self.display_mods(mods)
            
        except Exception as e:
            self.logger.error(f"Failed to load mods: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to load mods:\n{str(e)}"
            )
    
    def display_mods(self, mods: list):
        """Display mods in list"""
        self.mod_list.clear()
        
        for mod_data in mods:
            item = QListWidgetItem()
            
            # Set text
            text = f"{mod_data['name']}\n"
            text += f"v{mod_data['version']} by {mod_data['author']}\n"
            text += f"⭐ {mod_data.get('rating', 0):.1f} | "
            text += f"📥 {mod_data.get('downloads', 0):,}"
            
            item.setText(text)
            item.setData(Qt.ItemDataRole.UserRole, mod_data)
            
            self.mod_list.addItem(item)
        
        self.count_label.setText(f"Mods: {len(mods)}")
    
    def on_mod_selected(self, current, previous):
        """Handle mod selection"""
        if not current:
            return
        
        mod_data = current.data(Qt.ItemDataRole.UserRole)
        self.selected_mod = mod_data
        
        # Update details
        self.update_details(mod_data)
        
        # Enable download button
        self.download_btn.setEnabled(True)
    
    def update_details(self, mod_data: dict):
        """Update details panel with mod info"""
        # Update header
        self.mod_name_label.setText(f"<h2>{mod_data['name']}</h2>")
        self.mod_author_label.setText(f"by {mod_data['author']}")
        self.mod_version_label.setText(f"Version {mod_data['version']}")
        
        stats = f"⭐ {mod_data.get('rating', 0):.1f} | "
        stats += f"📥 {mod_data.get('downloads', 0):,} downloads"
        self.mod_stats_label.setText(stats)
        
        # Update icon
        # TODO: Load icon from URL or cache
        default_icon = Settings.RESOURCES_DIR / "icons" / "default_mod_icon.png"
        if default_icon.exists():
            pixmap = QPixmap(str(default_icon))
            self.mod_icon.setPixmap(pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio))
        
        # Update description
        description = mod_data.get('description', 'No description available')
        self.description_text.setPlainText(description)
        
        # Update dependencies
        self.dependencies_list.clear()
        deps = self.thunderstore.get_mod_dependencies(mod_data)
        
        if deps:
            for dep in deps:
                item = QListWidgetItem(f"• {dep['mod_id']} (v{dep['version']})")
                self.dependencies_list.addItem(item)
        else:
            item = QListWidgetItem("No dependencies")
            self.dependencies_list.addItem(item)
    
    def download_mod(self):
        """Download selected mod"""
        if not self.selected_mod:
            return
        
        self.logger.info(f"Downloading mod: {self.selected_mod['id']}")
        
        # Disable button and show progress
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start download worker
        self.download_worker = DownloadWorker(
            self.thunderstore,
            self.selected_mod
        )
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()
    
    def on_download_progress(self, current: int, total: int):
        """Update progress bar"""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
    
    def on_download_finished(self, success: bool, message: str):
        """Handle download completion"""
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        
        if success:
            # Process downloaded mod
            download_path = Path(message)
            
            # Extract and save to database
            # TODO: Implement extraction and processing
            
            QMessageBox.information(
                self,
                "Success",
                f"Mod '{self.selected_mod['name']}' downloaded successfully"
            )
            
            self.mod_downloaded.emit(self.selected_mod['id'])
            
        else:
            QMessageBox.critical(
                self,
                "Download Failed",
                f"Failed to download mod:\n{message}"
            )
    
    def on_search_changed(self, text: str):
        """Handle search text change"""
        # Debounce search
        # TODO: Implement debouncing
        self.apply_filters()
    
    def apply_filters(self):
        """Apply search and filters"""
        query = self.search_input.text()
        category = self.category_combo.currentText()
        sort_by = self.sort_combo.currentText().lower()
        
        # Search
        mods = self.thunderstore.search_mods(
            query=query,
            category=None if category == "All Categories" else category,
            sort_by=sort_by
        )
        
        self.display_mods(mods)
    
    def refresh(self):
        """Refresh mod list"""
        self.load_mods()
