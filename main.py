"""
Valheim Mod Manager - Main Entry Point
Version: 1.0.0
Author: Your Name
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from utils.logger import setup_logger
from ui.main_window import MainWindow
from core.database import Database


def setup_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        Settings.DATA_DIR,
        Settings.MODS_DIR,
        Settings.PROFILES_DIR,
        Settings.CONFIGS_DIR,
        Settings.CACHE_DIR,
        Settings.LOGS_DIR,
        Settings.BACKUPS_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def main():
    """Main application entry point"""
    # Setup logging
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("Starting Valheim Mod Manager v1.0.0")
    logger.info("=" * 60)
    
    try:
        # Create necessary directories
        setup_directories()
        logger.info("Directory structure initialized")
        
        # Initialize database
        db = Database()
        db.initialize()
        logger.info("Database initialized")
        
        # Create Qt Application
        app = QApplication(sys.argv)
        app.setApplicationName("Valheim Mod Manager")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("ValheimMods")
        
        # Set application icon
        icon_path = Settings.RESOURCES_DIR / "icons" / "app_icon.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
        
        # Load stylesheet
        stylesheet_path = Settings.RESOURCES_DIR / "styles" / "dark_theme.qss"
        if stylesheet_path.exists():
            with open(stylesheet_path, 'r') as f:
                app.setStyleSheet(f.read())
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("Application started successfully")
        
        # Start event loop
        exit_code = app.exec()
        
        logger.info(f"Application exited with code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.critical(f"Fatal error during startup: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
