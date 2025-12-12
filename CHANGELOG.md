# Changelog

All notable changes to Valheim Mod Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Automatic mod updates
- Cloud profile sync
- Modpack sharing
- Multi-language support
- In-app mod ratings

## [1.0.0] - 2024-12-12

### 🎉 Initial Release

#### Added
- **Core Features**
  - Browse and download mods from Thunderstore
  - Smart deployment with hash-based change detection
  - Profile management for multiple mod configurations
  - Automatic dependency resolution
  - Configuration file management
  - Game launcher integration
  
- **User Interface**
  - Modern PyQt6-based GUI
  - Browse Mods tab with search and filters
  - Repository tab for managing downloads
  - Profiles tab for mod organization
  - Configs tab for configuration editing
  - Settings tab for application preferences
  
- **Smart Deployment System**
  - Hash-based file change detection
  - Incremental deployment (only changed files)
  - Automatic backup before deployment
  - Rollback capability
  - Deployment state tracking
  
- **Dependency Management**
  - Topological sort for correct load order
  - Circular dependency detection
  - Version conflict detection
  - Automatic dependency resolution
  
- **Configuration System**
  - Profile-specific config overrides
  - Config validation with rules
  - Default config preservation
  - Config merge functionality
  - Backup and restore
  
- **Database**
  - SQLite storage with indexes
  - Mod metadata management
  - Deployment state tracking
  - Usage statistics
  - Settings persistence
  
- **Performance Optimizations**
  - LRU cache for icons and hashes
  - Lazy loading for large mod lists
  - Async download with progress tracking
  - Network retry with exponential backoff
  
- **Error Handling**
  - Comprehensive exception hierarchy
  - Automatic rollback on deployment failure
  - Detailed error logging
  - User-friendly error messages
  
- **Utilities**
  - Fast file hashing with xxHash
  - Safe file operations
  - Input validation
  - Logging with rotation
  
- **Documentation**
  - Comprehensive README
  - Quick Start Guide
  - Architecture documentation
  - Code examples and API reference

#### Technical Details
- Python 3.9+ support
- Cross-platform (Windows, Linux, macOS)
- PyQt6 for modern UI
- SQLite for data persistence
- xxHash for fast file hashing
- Requests with retry logic for network operations

#### Known Issues
- Icon caching may be slow on first load
- Large mod lists (1000+) may take time to filter
- Some BepInEx mods may require manual configuration

---

## Version History

### [0.9.0-beta] - 2024-12-01 (Pre-release)

#### Added
- Beta testing release
- Core functionality implementation
- Basic UI implementation

#### Fixed
- Various bug fixes from alpha testing
- Performance improvements
- UI responsiveness

### [0.5.0-alpha] - 2024-11-15 (Alpha)

#### Added
- Initial alpha release
- Basic mod browsing
- Simple profile system
- Manual deployment

---

## Upgrade Guide

### From 0.9.0-beta to 1.0.0
1. Backup your `data` folder
2. Install new version
3. Profiles and mods will be migrated automatically
4. Review changelog for breaking changes

---

## Breaking Changes

### 1.0.0
- None (initial release)

---

## Migration Notes

### Database Schema Changes
- Version 1.0.0 includes optimized indexes
- Existing databases will be automatically upgraded
- Backup recommended before upgrade

---

## Contributors

Thanks to everyone who contributed to this release:
- [Your Name] - Project Lead & Development
- Community testers - Bug reports and feedback
- Valheim modding community - Inspiration and support

---

## Links

- [GitHub Repository](https://github.com/yourusername/valheim-mod-manager)
- [Issue Tracker](https://github.com/yourusername/valheim-mod-manager/issues)
- [Wiki](https://github.com/yourusername/valheim-mod-manager/wiki)
- [Discord Community](https://discord.gg/example)

---

[Unreleased]: https://github.com/yourusername/valheim-mod-manager/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/valheim-mod-manager/releases/tag/v1.0.0
[0.9.0-beta]: https://github.com/yourusername/valheim-mod-manager/releases/tag/v0.9.0-beta
[0.5.0-alpha]: https://github.com/yourusername/valheim-mod-manager/releases/tag/v0.5.0-alpha
