"""
Build Script for Creating Executable with PyInstaller
"""

import sys
import os
import shutil
from pathlib import Path
import subprocess


class Builder:
    """Build executable using PyInstaller"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.spec_file = self.project_root / "ValheimModManager.spec"
    
    def clean(self):
        """Remove old build artifacts"""
        print("🧹 Cleaning old builds...")
        
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        
        if self.spec_file.exists():
            self.spec_file.unlink()
        
        print("✅ Clean complete")
    
    def create_spec_file(self):
        """Create PyInstaller spec file"""
        print("📝 Creating spec file...")
        
        spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('config', 'config'),
    ],
    hiddenimports=[
        'markdown',
        'xxhash',
        'tenacity',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'black', 'pylint', 'mypy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ValheimModManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app_icon.ico' if os.path.exists('resources/icons/app_icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ValheimModManager',
)
"""
        
        with open(self.spec_file, 'w') as f:
            f.write(spec_content.strip())
        
        print("✅ Spec file created")
    
    def build(self):
        """Run PyInstaller build"""
        print("🔨 Building executable...")
        
        try:
            subprocess.run(
                ['pyinstaller', str(self.spec_file), '--clean'],
                check=True,
                cwd=str(self.project_root)
            )
            print("✅ Build complete")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            return False
    
    def create_portable_package(self):
        """Create portable package with all necessary files"""
        print("📦 Creating portable package...")
        
        portable_dir = self.dist_dir / "ValheimModManager_Portable"
        portable_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy executable and dependencies
        app_dir = self.dist_dir / "ValheimModManager"
        if app_dir.exists():
            shutil.copytree(app_dir, portable_dir / "app", dirs_exist_ok=True)
        
        # Create data directories
        (portable_dir / "data").mkdir(exist_ok=True)
        (portable_dir / "data" / "mods").mkdir(exist_ok=True)
        (portable_dir / "data" / "profiles").mkdir(exist_ok=True)
        (portable_dir / "data" / "configs").mkdir(exist_ok=True)
        
        # Copy documentation
        readme_src = self.project_root / "README.md"
        if readme_src.exists():
            shutil.copy(readme_src, portable_dir / "README.md")
        
        # Create startup script
        if sys.platform == "win32":
            startup_script = portable_dir / "ValheimModManager.bat"
            startup_script.write_text("""
@echo off
cd /d "%~dp0"
start "" "app\\ValheimModManager.exe"
""".strip())
        else:
            startup_script = portable_dir / "ValheimModManager.sh"
            startup_script.write_text("""
#!/bin/bash
cd "$(dirname "$0")"
./app/ValheimModManager
""".strip())
            startup_script.chmod(0o755)
        
        print("✅ Portable package created")
    
    def create_zip(self):
        """Create ZIP archive of portable package"""
        print("📦 Creating ZIP archive...")
        
        portable_dir = self.dist_dir / "ValheimModManager_Portable"
        if not portable_dir.exists():
            print("❌ Portable package not found")
            return
        
        import zipfile
        
        zip_path = self.dist_dir / "ValheimModManager_v1.0.0.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in portable_dir.rglob('*'):
                if file.is_file():
                    arcname = file.relative_to(portable_dir.parent)
                    zipf.write(file, arcname)
        
        print(f"✅ ZIP archive created: {zip_path}")
    
    def print_build_info(self):
        """Print build information"""
        print("\n" + "=" * 60)
        print("📊 Build Information")
        print("=" * 60)
        
        app_dir = self.dist_dir / "ValheimModManager"
        if app_dir.exists():
            total_size = sum(
                f.stat().st_size for f in app_dir.rglob('*') if f.is_file()
            )
            print(f"📁 Build directory: {app_dir}")
            print(f"💾 Total size: {total_size / (1024*1024):.1f} MB")
        
        zip_path = self.dist_dir / "ValheimModManager_v1.0.0.zip"
        if zip_path.exists():
            zip_size = zip_path.stat().st_size
            print(f"📦 ZIP archive: {zip_path}")
            print(f"💾 ZIP size: {zip_size / (1024*1024):.1f} MB")
        
        print("=" * 60 + "\n")
    
    def run(self):
        """Run complete build process"""
        print("\n🚀 Starting build process...\n")
        
        # Step 1: Clean
        self.clean()
        
        # Step 2: Create spec file
        self.create_spec_file()
        
        # Step 3: Build with PyInstaller
        if not self.build():
            print("\n❌ Build failed!")
            return False
        
        # Step 4: Create portable package
        self.create_portable_package()
        
        # Step 5: Create ZIP
        self.create_zip()
        
        # Step 6: Print info
        self.print_build_info()
        
        print("✅ Build process complete!")
        print(f"\n📁 Output directory: {self.dist_dir}")
        
        return True


def main():
    """Main entry point"""
    builder = Builder()
    success = builder.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
