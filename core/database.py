"""
SQLite Database Manager with Hash Tracking
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from config.settings import Settings
from core.models import Mod, ModDependency, ModConfig
from core.exceptions import DatabaseError, DatabaseConnectionError, DatabaseQueryError
from utils.logger import LoggerMixin


class Database(LoggerMixin):
    """Manages SQLite database operations"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Settings.DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = None
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise DatabaseConnectionError(f"Database connection failed: {e}")
        finally:
            if conn:
                conn.close()
    
    def initialize(self):
        """Initialize database schema"""
        self.logger.info("Initializing database schema")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Mods table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mods (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    author TEXT NOT NULL,
                    version TEXT NOT NULL,
                    description TEXT,
                    full_description TEXT,
                    download_url TEXT,
                    file_size INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    downloads INTEGER DEFAULT 0,
                    icon_path TEXT,
                    readme_path TEXT,
                    changelog_path TEXT,
                    install_path TEXT,
                    manifest_json TEXT,
                    config_files TEXT,
                    tags TEXT,
                    enabled INTEGER DEFAULT 1,
                    load_order INTEGER DEFAULT 0,
                    installed INTEGER DEFAULT 0,
                    update_available INTEGER DEFAULT 0,
                    last_updated TIMESTAMP,
                    downloaded_at TIMESTAMP,
                    last_used TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Dependencies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mod_id TEXT NOT NULL,
                    depends_on TEXT NOT NULL,
                    version_constraint TEXT DEFAULT '*',
                    FOREIGN KEY (mod_id) REFERENCES mods(id) ON DELETE CASCADE,
                    UNIQUE(mod_id, depends_on)
                )
            """)
            
            # Deployment state table (for smart copy)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deployment_state (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    mod_id TEXT,
                    profile_name TEXT,
                    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mod_id) REFERENCES mods(id) ON DELETE CASCADE
                )
            """)
            
            # Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Download cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS download_cache (
                    url TEXT PRIMARY KEY,
                    etag TEXT,
                    last_modified TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Usage statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mod_id TEXT,
                    profile_name TEXT,
                    action TEXT,
                    launched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mod_id) REFERENCES mods(id) ON DELETE CASCADE
                )
            """)
            
            # Backup records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_name TEXT NOT NULL,
                    backup_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    size_bytes INTEGER DEFAULT 0,
                    notes TEXT
                )
            """)
            
            # Create indexes for performance
            self._create_indexes(cursor)
            
            self.logger.info("Database schema initialized successfully")
    
    def _create_indexes(self, cursor):
        """Create database indexes"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_mods_author ON mods(author)",
            "CREATE INDEX IF NOT EXISTS idx_mods_installed ON mods(installed)",
            "CREATE INDEX IF NOT EXISTS idx_mods_tags ON mods(tags)",
            "CREATE INDEX IF NOT EXISTS idx_dependencies_mod_id ON dependencies(mod_id)",
            "CREATE INDEX IF NOT EXISTS idx_dependencies_depends_on ON dependencies(depends_on)",
            "CREATE INDEX IF NOT EXISTS idx_deployment_state_mod_id ON deployment_state(mod_id)",
            "CREATE INDEX IF NOT EXISTS idx_deployment_state_profile ON deployment_state(profile_name)",
            "CREATE INDEX IF NOT EXISTS idx_usage_stats_mod_id ON usage_stats(mod_id)",
            "CREATE INDEX IF NOT EXISTS idx_usage_stats_time ON usage_stats(launched_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_backups_profile ON backups(profile_name)",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    # Mod operations
    def save_mod(self, mod: Mod) -> bool:
        """Save or update mod in database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Prepare data
                data = {
                    'id': mod.id,
                    'name': mod.name,
                    'author': mod.author,
                    'version': mod.version,
                    'description': mod.description,
                    'full_description': mod.full_description,
                    'download_url': mod.download_url,
                    'file_size': mod.file_size,
                    'rating': mod.rating,
                    'downloads': mod.downloads,
                    'icon_path': str(mod.icon_path) if mod.icon_path else None,
                    'readme_path': str(mod.readme_path) if mod.readme_path else None,
                    'changelog_path': str(mod.changelog_path) if mod.changelog_path else None,
                    'install_path': str(mod.install_path) if mod.install_path else None,
                    'manifest_json': str(mod.manifest),
                    'config_files': ','.join(mod.config_files),
                    'tags': ','.join(mod.tags),
                    'enabled': 1 if mod.enabled else 0,
                    'load_order': mod.load_order,
                    'installed': 1 if mod.installed else 0,
                    'update_available': 1 if mod.update_available else 0,
                    'last_updated': mod.last_updated,
                    'downloaded_at': mod.downloaded_at or datetime.now(),
                    'last_used': mod.last_used,
                }
                
                cursor.execute("""
                    INSERT OR REPLACE INTO mods 
                    (id, name, author, version, description, full_description,
                     download_url, file_size, rating, downloads,
                     icon_path, readme_path, changelog_path, install_path,
                     manifest_json, config_files, tags,
                     enabled, load_order, installed, update_available,
                     last_updated, downloaded_at, last_used)
                    VALUES 
                    (:id, :name, :author, :version, :description, :full_description,
                     :download_url, :file_size, :rating, :downloads,
                     :icon_path, :readme_path, :changelog_path, :install_path,
                     :manifest_json, :config_files, :tags,
                     :enabled, :load_order, :installed, :update_available,
                     :last_updated, :downloaded_at, :last_used)
                """, data)
                
                # Save dependencies
                cursor.execute("DELETE FROM dependencies WHERE mod_id = ?", (mod.id,))
                for dep in mod.dependencies:
                    cursor.execute("""
                        INSERT INTO dependencies (mod_id, depends_on, version_constraint)
                        VALUES (?, ?, ?)
                    """, (mod.id, dep.mod_id, dep.version_constraint))
                
                self.logger.info(f"Saved mod: {mod.id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save mod {mod.id}: {e}")
            raise DatabaseQueryError(f"Failed to save mod: {e}")
    
    def get_mod(self, mod_id: str) -> Optional[Mod]:
        """Get mod by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM mods WHERE id = ?", (mod_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Get dependencies
                cursor.execute("""
                    SELECT depends_on, version_constraint 
                    FROM dependencies 
                    WHERE mod_id = ?
                """, (mod_id,))
                deps = [
                    ModDependency(mod_id=r['depends_on'], version_constraint=r['version_constraint'])
                    for r in cursor.fetchall()
                ]
                
                return self._row_to_mod(row, deps)
                
        except Exception as e:
            self.logger.error(f"Failed to get mod {mod_id}: {e}")
            return None
    
    def get_all_mods(self, installed_only: bool = False) -> List[Mod]:
        """Get all mods"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if installed_only:
                    cursor.execute("SELECT * FROM mods WHERE installed = 1 ORDER BY name")
                else:
                    cursor.execute("SELECT * FROM mods ORDER BY name")
                
                mods = []
                for row in cursor.fetchall():
                    mod_id = row['id']
                    
                    # Get dependencies
                    cursor.execute("""
                        SELECT depends_on, version_constraint 
                        FROM dependencies 
                        WHERE mod_id = ?
                    """, (mod_id,))
                    deps = [
                        ModDependency(mod_id=r['depends_on'], version_constraint=r['version_constraint'])
                        for r in cursor.fetchall()
                    ]
                    
                    mods.append(self._row_to_mod(row, deps))
                
                return mods
                
        except Exception as e:
            self.logger.error(f"Failed to get mods: {e}")
            return []
    
    def delete_mod(self, mod_id: str) -> bool:
        """Delete mod from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM mods WHERE id = ?", (mod_id,))
                self.logger.info(f"Deleted mod: {mod_id}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to delete mod {mod_id}: {e}")
            return False
    
    def search_mods(self, query: str, tags: List[str] = None) -> List[Mod]:
        """Search mods by name, author, or description"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                    SELECT * FROM mods 
                    WHERE (name LIKE ? OR author LIKE ? OR description LIKE ?)
                """
                params = [f"%{query}%", f"%{query}%", f"%{query}%"]
                
                if tags:
                    tag_conditions = " AND ".join(["tags LIKE ?" for _ in tags])
                    sql += f" AND ({tag_conditions})"
                    params.extend([f"%{tag}%" for tag in tags])
                
                sql += " ORDER BY downloads DESC, rating DESC"
                
                cursor.execute(sql, params)
                
                mods = []
                for row in cursor.fetchall():
                    mod_id = row['id']
                    cursor.execute("""
                        SELECT depends_on, version_constraint 
                        FROM dependencies 
                        WHERE mod_id = ?
                    """, (mod_id,))
                    deps = [
                        ModDependency(mod_id=r['depends_on'], version_constraint=r['version_constraint'])
                        for r in cursor.fetchall()
                    ]
                    mods.append(self._row_to_mod(row, deps))
                
                return mods
                
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def _row_to_mod(self, row: sqlite3.Row, dependencies: List[ModDependency]) -> Mod:
        """Convert database row to Mod object"""
        return Mod(
            id=row['id'],
            name=row['name'],
            author=row['author'],
            version=row['version'],
            description=row['description'] or "",
            full_description=row['full_description'] or "",
            download_url=row['download_url'] or "",
            file_size=row['file_size'],
            rating=row['rating'],
            downloads=row['downloads'],
            icon_path=Path(row['icon_path']) if row['icon_path'] else None,
            readme_path=Path(row['readme_path']) if row['readme_path'] else None,
            changelog_path=Path(row['changelog_path']) if row['changelog_path'] else None,
            install_path=Path(row['install_path']) if row['install_path'] else None,
            manifest=eval(row['manifest_json']) if row['manifest_json'] else {},
            dependencies=dependencies,
            config_files=row['config_files'].split(',') if row['config_files'] else [],
            tags=row['tags'].split(',') if row['tags'] else [],
            enabled=bool(row['enabled']),
            load_order=row['load_order'],
            installed=bool(row['installed']),
            update_available=bool(row['update_available']),
            last_updated=row['last_updated'],
            downloaded_at=row['downloaded_at'],
            last_used=row['last_used'],
        )
    
    # Deployment state operations
    def save_deployment_state(self, file_path: str, file_hash: str, mod_id: str, profile_name: str):
        """Save file deployment state"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO deployment_state 
                    (file_path, file_hash, mod_id, profile_name, deployed_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (file_path, file_hash, mod_id, profile_name, datetime.now()))
        except Exception as e:
            self.logger.error(f"Failed to save deployment state: {e}")
    
    def get_deployment_state(self, profile_name: str = None) -> Dict[str, str]:
        """Get deployment state (file_path -> hash mapping)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if profile_name:
                    cursor.execute("""
                        SELECT file_path, file_hash 
                        FROM deployment_state 
                        WHERE profile_name = ?
                    """, (profile_name,))
                else:
                    cursor.execute("SELECT file_path, file_hash FROM deployment_state")
                
                return {row['file_path']: row['file_hash'] for row in cursor.fetchall()}
        except Exception as e:
            self.logger.error(f"Failed to get deployment state: {e}")
            return {}
    
    def clear_deployment_state(self, profile_name: str = None):
        """Clear deployment state"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if profile_name:
                    cursor.execute("DELETE FROM deployment_state WHERE profile_name = ?", (profile_name,))
                else:
                    cursor.execute("DELETE FROM deployment_state")
        except Exception as e:
            self.logger.error(f"Failed to clear deployment state: {e}")
    
    # Settings operations
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting value"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row['value'] if row else default
        except Exception as e:
            self.logger.error(f"Failed to get setting {key}: {e}")
            return default
    
    def set_setting(self, key: str, value: Any):
        """Set setting value"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                """, (key, str(value), datetime.now()))
        except Exception as e:
            self.logger.error(f"Failed to set setting {key}: {e}")
    
    # Usage statistics
    def log_usage(self, mod_id: str, profile_name: str, action: str = "launch"):
        """Log mod usage"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO usage_stats (mod_id, profile_name, action)
                    VALUES (?, ?, ?)
                """, (mod_id, profile_name, action))
        except Exception as e:
            self.logger.error(f"Failed to log usage: {e}")
    
    def get_popular_mods(self, limit: int = 10) -> List[tuple]:
        """Get most used mods"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT mod_id, COUNT(*) as usage_count
                    FROM usage_stats
                    WHERE launched_at > datetime('now', '-30 days')
                    GROUP BY mod_id
                    ORDER BY usage_count DESC
                    LIMIT ?
                """, (limit,))
                return [(row['mod_id'], row['usage_count']) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get popular mods: {e}")
            return []
