# 🎮 Valheim Mod Manager

A modern, feature-rich mod manager for Valheim with smart deployment, dependency resolution, and profile management.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

## ✨ Features

### Core Features
- **📦 Browse & Download Mods** - Direct integration with Thunderstore API
- **🚀 Smart Deployment** - Hash-based change detection for efficient deployment
- **👥 Profile Management** - Multiple mod configurations with easy switching
- **🔗 Automatic Dependency Resolution** - No more missing dependencies
- **⚙️ Configuration Management** - Profile-specific config overrides
- **🔄 Update Checker** - Keep your mods up to date
- **📊 Usage Statistics** - Track your most-used mods

### Technical Features
- **Hash-Based Smart Copy** - Only copies changed files
- **Circular Dependency Detection** - Prevents invalid configurations
- **Automatic Rollback** - Safe deployment with checkpoint system
- **Conflict Detection** - Warns about file conflicts between mods
- **LRU Caching** - Fast icon and hash lookups
- **Retry Logic** - Reliable downloads with automatic retries

## 📋 Requirements

- Python 3.9 or higher
- Windows 10/11, Linux, or macOS
- Valheim installed (Steam version)
- BepInEx (will be installed automatically if missing)

## 🚀 Quick Start

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/valheim-mod-manager.git
cd valheim-mod-manager
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
python main.py
```

### First-Time Setup

1. **Set Game Path**
   - Go to Settings tab
   - Click "Browse" and select your Valheim installation directory
   - Usually: `C:\Program Files (x86)\Steam\steamapps\common\Valheim`

2. **Create a Profile**
   - Go to Profiles tab
   - Click "New Profile"
   - Give it a name (e.g., "Quality of Life")

3. **Browse and Install Mods**
   - Go to Browse Mods tab
   - Search for mods
   - Click "Download" on mods you want

4. **Add Mods to Profile**
   - Go to Profiles tab
   - Select your profile
   - Click "Add Mods"
   - Select mods from your repository

5. **Launch Game**
   - Select profile from dropdown
   - Click "🚀 Launch Game"

## 📖 Usage Guide

### Managing Mods

#### Downloading Mods
1. Navigate to **Browse Mods** tab
2. Use search bar or filters to find mods
3. Click on a mod to view details
4. Click **Download** button
5. Mod will be added to your repository

#### Installing to Profile
1. Go to **Profiles** tab
2. Select your profile
3. Click **Add Mods** button
4. Select mods from repository
5. Click **OK**

#### Enabling/Disabling Mods
- Check/uncheck mods in the profile mod list
- Changes take effect on next deployment

### Profile Management

#### Creating Profiles
1. Profiles tab → **New Profile**
2. Enter profile name and description
3. Add mods from repository
4. Configure mod settings

#### Switching Profiles
1. Use profile dropdown in top toolbar
2. Select desired profile
3. Click **Launch Game** to deploy and start

#### Exporting/Importing Profiles
- **Export**: File → Export Profile (saves as JSON)
- **Import**: File → Import Profile (loads from JSON)

### Configuration Management

#### Editing Mod Configs
1. Go to **Configs** tab
2. Select profile and mod
3. Edit configuration values
4. Click **Save**

#### Profile-Specific Configs
- Each profile can have custom config overrides
- Default configs are used if no override exists
- Click **Reset to Default** to remove overrides

### Deployment System

#### How Smart Deployment Works
1. **Hash Calculation** - Calculates hash of each file
2. **Change Detection** - Compares with previous deployment
3. **Incremental Copy** - Only copies changed files
4. **State Tracking** - Saves deployment state to database

#### Rollback
- Automatic checkpoint before deployment
- Use Tools → Rollback if issues occur
- Restores previous working state

## 🏗️ Architecture

### High-Level Overview
```
┌─────────────────────────────────────────┐
│         User Interface (PyQt6)          │
│  ┌─────────┬─────────┬────────┬──────┐ │
│  │ Browse  │Repository│Profiles│Config│ │
│  └─────────┴─────────┴────────┴──────┘ │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         Business Logic Layer            │
│  ┌──────────┬──────────┬──────────────┐│
│  │Thunderst.│Deployment│ Dependency   ││
│  │  Client  │  Engine  │  Resolver    ││
│  └──────────┴──────────┴──────────────┘│
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│            Data Layer                   │
│  ┌──────────┬──────────┬──────────────┐│
│  │ SQLite   │  File    │     Cache    ││
│  │ Database │  System  │    Manager   ││
│  └──────────┴──────────┴──────────────┘│
└─────────────────────────────────────────┘
```

### Key Components

#### Core
- **Database** - SQLite storage with indexes
- **Models** - Data classes (Mod, Profile, ModConfig)
- **Exceptions** - Custom exception hierarchy

#### Services
- **ThunderstoreClient** - API integration with caching
- **ModManager** - Mod lifecycle management
- **DeploymentEngine** - Smart deployment system
- **ConfigManager** - Configuration file handling
- **GameLauncher** - Game process management
- **DependencyResolver** - Topological sort for load order

#### Utilities
- **HashUtils** - Fast file hashing with xxHash
- **FileUtils** - Safe file operations
- **Logger** - Centralized logging with rotation

## 🔧 Configuration

### Application Settings

Edit `config/settings.py` to customize:

```python
# Network Settings
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
CACHE_DURATION_HOURS = 6

# Performance Settings
MAX_ICON_CACHE_SIZE = 100
LAZY_LOAD_THRESHOLD = 100

# Backup Settings
MAX_BACKUPS_PER_PROFILE = 5
AUTO_BACKUP_BEFORE_DEPLOY = True

# Feature Flags
ENABLE_AUTO_UPDATE = True
ENABLE_CONFLICT_DETECTION = True
ENABLE_DEPENDENCY_AUTO_RESOLVE = True
```

### Validation Rules

Add custom validation rules in `ConfigValidationRules`:

```python
CUSTOM_MOD_RULES = {
    "ModSection": {
        "settingKey": {
            "type": int,
            "min": 0,
            "max": 100,
            "default": 50
        }
    }
}
```

## 🛠️ Development

### Project Structure

```
valheim_mod_manager/
├── main.py                 # Entry point
├── config/                 # Configuration
│   ├── settings.py
│   └── paths.py
├── core/                   # Core logic
│   ├── database.py
│   ├── models.py
│   └── exceptions.py
├── services/               # Business logic
│   ├── thunderstore_client.py
│   ├── mod_manager.py
│   ├── deployment_engine.py
│   ├── config_manager.py
│   ├── game_launcher.py
│   └── dependency_resolver.py
├── ui/                     # User interface
│   ├── main_window.py
│   └── tabs/
├── utils/                  # Utilities
│   ├── logger.py
│   ├── hash_utils.py
│   └── file_utils.py
└── tests/                  # Unit tests
```

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
black .

# Lint code
pylint valheim_mod_manager/

# Type check
mypy valheim_mod_manager/
```

### Building Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build
python scripts/build.py

# Output in dist/ValheimModManager/
```

## 🐛 Troubleshooting

### Common Issues

#### "Game path not found"
- Manually set game path in Settings
- Ensure Valheim is installed via Steam

#### "Deployment failed"
- Check file permissions
- Ensure game is not running
- Check logs in `data/logs/`

#### "Mod conflicts detected"
- Review conflicting mods in Profiles tab
- Disable conflicting mods or check compatibility

#### "Download failed"
- Check internet connection
- Try refreshing mod list (F5)
- Check Thunderstore API status

### Debug Mode

Enable debug logging:
```python
# In config/settings.py
LOG_LEVEL = "DEBUG"
```

View logs:
- Help → View Logs
- Or check `data/logs/valheim_mod_manager.log`

## 📚 API Reference

### Core Classes

#### Mod
```python
mod = Mod(
    id="Author-ModName",
    name="Mod Name",
    version="1.0.0",
    ...
)

# Get dependencies
deps = mod.dependencies

# Check if enabled
if mod.enabled:
    ...
```

#### Profile
```python
profile = Profile(name="My Profile")

# Add mod
profile.add_mod(mod)

# Get enabled mods
mods = profile.get_enabled_mods()

# Export
profile.export_to_json(path)
```

#### DeploymentEngine
```python
engine = DeploymentEngine()

# Deploy profile
engine.deploy_profile(profile, progress_callback)

# Rollback
checkpoint = engine.create_checkpoint(profile)
engine.rollback(checkpoint)
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Development Guidelines
- Follow PEP 8 style guide
- Add docstrings to functions
- Include type hints
- Write unit tests
- Update documentation

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- [Thunderstore](https://thunderstore.io/) for mod hosting API
- [BepInEx](https://github.com/BepInEx/BepInEx) for modding framework
- [Iron Gate Studio](https://www.irongatestudio.se/) for Valheim
- Community mod developers

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/valheim-mod-manager/issues)
- **Discord**: [Join our server](#)
- **Wiki**: [Documentation](https://github.com/yourusername/valheim-mod-manager/wiki)

## 🗺️ Roadmap

### Version 1.1
- [ ] Mod update notifications
- [ ] Automatic dependency installation
- [ ] Conflict resolution suggestions

### Version 1.2
- [ ] Cloud profile sync
- [ ] Modpack sharing
- [ ] In-app mod ratings

### Version 2.0
- [ ] Performance profiling
- [ ] Crash report integration
- [ ] Multi-language support

---

Made with ❤️ for the Valheim community
