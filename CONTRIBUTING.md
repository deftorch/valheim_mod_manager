# Contributing to Valheim Mod Manager

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Areas for Contribution](#areas-for-contribution)

## 🤝 Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community

**Unacceptable behavior:**
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Basic understanding of PyQt6
- Familiarity with async programming

### First Contribution

1. **Find an Issue**
   - Look for issues labeled `good first issue` or `help wanted`
   - Comment on the issue to express interest
   - Wait for assignment before starting work

2. **Fork the Repository**
   ```bash
   git clone https://github.com/yourusername/valheim-mod-manager.git
   cd valheim-mod-manager
   ```

3. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 💻 Development Setup

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/valheim-mod-manager.git
cd valheim-mod-manager

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-qt pytest-cov black pylint mypy
```

### 2. Run Development Version

```bash
python main.py
```

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_database.py

# Run with verbose output
pytest -v
```

## 📁 Project Structure

```
valheim_mod_manager/
├── main.py                 # Entry point
├── config/                 # Configuration and settings
├── core/                   # Core data models and database
├── services/               # Business logic services
├── ui/                     # User interface components
│   ├── tabs/              # Tab implementations
│   ├── dialogs/           # Dialog windows
│   └── widgets/           # Custom widgets
├── utils/                  # Utility functions
├── tests/                  # Unit and integration tests
└── resources/              # Icons, styles, docs
```

### Key Modules

- **Database** (`core/database.py`) - SQLite operations
- **Models** (`core/models.py`) - Data structures
- **Deployment Engine** (`services/deployment_engine.py`) - Smart deployment
- **Dependency Resolver** (`services/dependency_resolver.py`) - Load order
- **Config Manager** (`services/config_manager.py`) - Config handling

## 📝 Coding Standards

### Python Style

We follow **PEP 8** with some modifications:

```python
# Good
def calculate_hash(file_path: Path) -> str:
    """Calculate file hash using xxhash"""
    if not file_path.exists():
        return ""
    
    hasher = xxhash.xxh64()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    
    return hasher.hexdigest()

# Bad
def calcHash(filePath):
    hasher=xxhash.xxh64()
    f=open(filePath,'rb')
    # ... missing docstring, type hints, error handling
```

### Type Hints

**Required** for all public functions:

```python
from typing import List, Optional, Dict

def search_mods(
    query: str,
    category: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """Search mods with filters"""
    pass
```

### Docstrings

Use **Google-style docstrings**:

```python
def deploy_profile(
    profile: Profile,
    game_path: Path,
    progress_callback: Optional[Callable] = None
) -> bool:
    """
    Deploy profile to game directory
    
    Args:
        profile: Profile to deploy
        game_path: Path to Valheim installation
        progress_callback: Optional progress callback
    
    Returns:
        True if deployment successful
    
    Raises:
        DeploymentError: If deployment fails
    
    Example:
        >>> engine.deploy_profile(my_profile, game_path)
        True
    """
    pass
```

### Error Handling

Always use custom exceptions:

```python
# Good
try:
    mod = self.db.get_mod(mod_id)
    if not mod:
        raise ModNotFoundError(f"Mod not found: {mod_id}")
except DatabaseError as e:
    self.logger.error(f"Database error: {e}")
    raise

# Bad
try:
    mod = db.get_mod(mod_id)
except:
    pass  # Silent failure
```

### Logging

Use the logger mixin:

```python
from utils.logger import LoggerMixin

class MyClass(LoggerMixin):
    def my_method(self):
        self.logger.info("Starting operation")
        self.logger.debug("Debug details")
        self.logger.warning("Something unusual")
        self.logger.error("Error occurred")
```

### Code Formatting

Format code with **Black**:

```bash
# Format all files
black .

# Check without writing
black --check .
```

### Linting

Use **Pylint**:

```bash
# Lint specific file
pylint core/database.py

# Lint entire project
pylint valheim_mod_manager/
```

## 🧪 Testing

### Writing Tests

```python
import pytest
from core.database import Database

class TestDatabase:
    """Test Database class"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary test database"""
        db = Database(":memory:")
        db.initialize()
        yield db
    
    def test_save_mod(self, temp_db):
        """Test saving mod to database"""
        mod = Mod(id="Test-Mod", name="Test", ...)
        
        result = temp_db.save_mod(mod)
        assert result is True
        
        saved_mod = temp_db.get_mod("Test-Mod")
        assert saved_mod is not None
        assert saved_mod.name == "Test"
```

### Test Coverage

Aim for **>80% coverage**:

```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html
```

### UI Testing

Use **pytest-qt**:

```python
def test_main_window(qtbot):
    """Test main window creation"""
    window = MainWindow()
    qtbot.addWidget(window)
    
    assert window.windowTitle() == "Valheim Mod Manager v1.0.0"
```

## 📤 Submitting Changes

### 1. Commit Messages

Follow **Conventional Commits**:

```bash
# Format: <type>(<scope>): <subject>

feat(ui): add dark theme toggle
fix(database): resolve query timeout issue
docs(readme): update installation instructions
test(core): add tests for dependency resolver
refactor(services): simplify config manager
chore(deps): update PyQt6 to 6.6.1
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `chore`: Maintenance
- `perf`: Performance improvement

### 2. Pull Request Process

1. **Update your branch**
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-branch
   git rebase main
   ```

2. **Run tests**
   ```bash
   pytest
   black --check .
   pylint valheim_mod_manager/
   ```

3. **Create PR**
   - Use descriptive title
   - Reference related issues
   - Describe changes made
   - Add screenshots if UI changes

4. **PR Template**
   ```markdown
   ## Description
   Brief description of changes
   
   ## Related Issues
   Closes #123
   
   ## Changes Made
   - Added feature X
   - Fixed bug Y
   - Updated docs
   
   ## Testing
   - [ ] Unit tests pass
   - [ ] Manual testing completed
   - [ ] No new warnings
   
   ## Screenshots
   (if applicable)
   ```

### 3. Code Review

- Address reviewer comments
- Keep discussions professional
- Be open to suggestions
- Request re-review when ready

## 🎯 Areas for Contribution

### High Priority

- **UI Improvements**
  - Dark/Light theme implementation
  - Icon caching optimization
  - Better progress indicators

- **Features**
  - Cloud profile sync
  - Modpack sharing
  - Automatic updates

- **Bug Fixes**
  - Check issue tracker
  - Test edge cases

### Documentation

- **User Documentation**
  - Video tutorials
  - FAQ expansion
  - Troubleshooting guides

- **Developer Documentation**
  - API documentation
  - Architecture diagrams
  - Code examples

### Testing

- **Unit Tests**
  - Increase coverage
  - Test edge cases

- **Integration Tests**
  - End-to-end workflows
  - UI testing

### Localization

- Translate to other languages
- Create language packs

## 🐛 Reporting Bugs

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What should happen

**Screenshots**
If applicable

**Environment:**
 - OS: [e.g. Windows 11]
 - Python Version: [e.g. 3.11]
 - App Version: [e.g. 1.0.0]

**Logs**
Attach log file from data/logs/
```

## 💡 Feature Requests

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
Description of problem

**Describe the solution you'd like**
Clear description of desired feature

**Describe alternatives you've considered**
Other approaches

**Additional context**
Screenshots, mockups, etc.
```

## 📞 Getting Help

- **Discord**: Join our community server
- **GitHub Discussions**: Ask questions
- **Email**: developer@example.com

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Mentioned in README.md (major contributions)

Thank you for contributing! 🎉
