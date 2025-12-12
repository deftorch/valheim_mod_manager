"""
Unit tests for Database module
"""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile

from core.database import Database
from core.models import Mod, ModDependency


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    db = Database(db_path)
    db.initialize()
    
    yield db
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sample_mod():
    """Create sample mod for testing"""
    return Mod(
        id="TestAuthor-TestMod",
        name="Test Mod",
        author="TestAuthor",
        version="1.0.0",
        description="A test mod",
        dependencies=[
            ModDependency(mod_id="BepInEx-BepInExPack", version_constraint=">=5.4.0")
        ],
        installed=True
    )


class TestDatabase:
    """Test Database class"""
    
    def test_initialize(self, temp_db):
        """Test database initialization"""
        assert temp_db.db_path.exists()
        
        # Check tables exist
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'mods', 'dependencies', 'deployment_state',
                'settings', 'download_cache', 'usage_stats', 'backups'
            ]
            
            for table in expected_tables:
                assert table in tables
    
    def test_save_mod(self, temp_db, sample_mod):
        """Test saving mod to database"""
        result = temp_db.save_mod(sample_mod)
        assert result is True
        
        # Verify mod was saved
        saved_mod = temp_db.get_mod(sample_mod.id)
        assert saved_mod is not None
        assert saved_mod.id == sample_mod.id
        assert saved_mod.name == sample_mod.name
        assert saved_mod.version == sample_mod.version
    
    def test_get_mod(self, temp_db, sample_mod):
        """Test retrieving mod from database"""
        temp_db.save_mod(sample_mod)
        
        retrieved_mod = temp_db.get_mod(sample_mod.id)
        
        assert retrieved_mod is not None
        assert retrieved_mod.id == sample_mod.id
        assert retrieved_mod.name == sample_mod.name
        assert retrieved_mod.author == sample_mod.author
        assert len(retrieved_mod.dependencies) == len(sample_mod.dependencies)
    
    def test_get_mod_not_found(self, temp_db):
        """Test getting non-existent mod"""
        result = temp_db.get_mod("NonExistent-Mod")
        assert result is None
    
    def test_get_all_mods(self, temp_db, sample_mod):
        """Test getting all mods"""
        # Save multiple mods
        temp_db.save_mod(sample_mod)
        
        mod2 = Mod(
            id="Author2-Mod2",
            name="Second Mod",
            author="Author2",
            version="2.0.0",
            installed=True
        )
        temp_db.save_mod(mod2)
        
        # Get all mods
        all_mods = temp_db.get_all_mods()
        assert len(all_mods) == 2
        
        # Get only installed
        installed = temp_db.get_all_mods(installed_only=True)
        assert len(installed) == 2
    
    def test_delete_mod(self, temp_db, sample_mod):
        """Test deleting mod"""
        temp_db.save_mod(sample_mod)
        
        # Delete mod
        result = temp_db.delete_mod(sample_mod.id)
        assert result is True
        
        # Verify deleted
        assert temp_db.get_mod(sample_mod.id) is None
    
    def test_search_mods(self, temp_db):
        """Test searching mods"""
        # Create test mods
        mod1 = Mod(
            id="Author1-BuildingMod",
            name="Building Helper",
            author="Author1",
            version="1.0.0",
            description="Helps with building"
        )
        
        mod2 = Mod(
            id="Author2-CombatMod",
            name="Combat Enhancer",
            author="Author2",
            version="1.0.0",
            description="Better combat"
        )
        
        temp_db.save_mod(mod1)
        temp_db.save_mod(mod2)
        
        # Search by name
        results = temp_db.search_mods("Building")
        assert len(results) == 1
        assert results[0].id == mod1.id
        
        # Search by author
        results = temp_db.search_mods("Author2")
        assert len(results) == 1
        assert results[0].id == mod2.id
    
    def test_deployment_state(self, temp_db):
        """Test deployment state operations"""
        # Save deployment state
        temp_db.save_deployment_state(
            "/path/to/file.dll",
            "abc123hash",
            "TestMod",
            "TestProfile"
        )
        
        # Get deployment state
        state = temp_db.get_deployment_state("TestProfile")
        assert "/path/to/file.dll" in state
        assert state["/path/to/file.dll"] == "abc123hash"
        
        # Clear deployment state
        temp_db.clear_deployment_state("TestProfile")
        state = temp_db.get_deployment_state("TestProfile")
        assert len(state) == 0
    
    def test_settings(self, temp_db):
        """Test settings operations"""
        # Set setting
        temp_db.set_setting("test_key", "test_value")
        
        # Get setting
        value = temp_db.get_setting("test_key")
        assert value == "test_value"
        
        # Get non-existent with default
        value = temp_db.get_setting("nonexistent", "default")
        assert value == "default"
    
    def test_usage_stats(self, temp_db, sample_mod):
        """Test usage statistics"""
        temp_db.save_mod(sample_mod)
        
        # Log usage
        temp_db.log_usage(sample_mod.id, "TestProfile", "launch")
        temp_db.log_usage(sample_mod.id, "TestProfile", "launch")
        
        # Get popular mods
        popular = temp_db.get_popular_mods(limit=10)
        assert len(popular) > 0
        assert popular[0][0] == sample_mod.id
        assert popular[0][1] == 2  # 2 launches


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for Database"""
    
    def test_mod_with_dependencies(self, temp_db):
        """Test saving and retrieving mod with dependencies"""
        mod = Mod(
            id="Complex-Mod",
            name="Complex Mod",
            author="ComplexAuthor",
            version="1.0.0",
            dependencies=[
                ModDependency(mod_id="Dep1", version_constraint=">=1.0.0"),
                ModDependency(mod_id="Dep2", version_constraint="*"),
            ]
        )
        
        temp_db.save_mod(mod)
        retrieved = temp_db.get_mod(mod.id)
        
        assert len(retrieved.dependencies) == 2
        assert any(d.mod_id == "Dep1" for d in retrieved.dependencies)
        assert any(d.mod_id == "Dep2" for d in retrieved.dependencies)
    
    def test_concurrent_operations(self, temp_db, sample_mod):
        """Test multiple operations in sequence"""
        # Save
        temp_db.save_mod(sample_mod)
        
        # Update
        sample_mod.version = "2.0.0"
        temp_db.save_mod(sample_mod)
        
        # Verify update
        updated = temp_db.get_mod(sample_mod.id)
        assert updated.version == "2.0.0"
        
        # Log usage
        temp_db.log_usage(sample_mod.id, "TestProfile")
        
        # Delete
        temp_db.delete_mod(sample_mod.id)
        
        # Verify deletion
        assert temp_db.get_mod(sample_mod.id) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
