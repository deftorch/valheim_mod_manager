"""
File Operations Utilities with Progress Tracking and Safety
"""

import shutil
import zipfile
from pathlib import Path
from typing import Callable, Optional, List
import tempfile
from datetime import datetime

from core.exceptions import (
    FileSystemError,
    ExtractionError,
    PermissionError as PermError
)
from utils.logger import LoggerMixin


class FileOperations(LoggerMixin):
    """Safe file operations with progress tracking"""
    
    @staticmethod
    def copy_with_progress(
        src: Path,
        dst: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Copy file with progress tracking
        
        Args:
            src: Source file path
            dst: Destination file path
            progress_callback: Optional callback(bytes_copied, total_bytes)
        
        Returns:
            True if successful
        """
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            total_size = src.stat().st_size
            copied = 0
            
            with open(src, 'rb') as fsrc:
                with open(dst, 'wb') as fdst:
                    while chunk := fsrc.read(8192):
                        fdst.write(chunk)
                        copied += len(chunk)
                        
                        if progress_callback:
                            progress_callback(copied, total_size)
            
            # Preserve metadata
            shutil.copystat(src, dst)
            return True
            
        except Exception as e:
            raise FileSystemError(f"Failed to copy {src} to {dst}: {e}")
    
    @staticmethod
    def safe_remove(path: Path, recursive: bool = False) -> bool:
        """
        Safely remove file or directory
        
        Args:
            path: Path to remove
            recursive: If True, remove directories recursively
        
        Returns:
            True if successful
        """
        try:
            if not path.exists():
                return True
            
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                if recursive:
                    shutil.rmtree(path)
                else:
                    path.rmdir()
            
            return True
            
        except PermissionError as e:
            raise PermError(f"Permission denied: {path}")
        except Exception as e:
            raise FileSystemError(f"Failed to remove {path}: {e}")
    
    @staticmethod
    def safe_move(src: Path, dst: Path) -> bool:
        """Safely move file or directory"""
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return True
        except Exception as e:
            raise FileSystemError(f"Failed to move {src} to {dst}: {e}")
    
    @staticmethod
    def create_backup(
        path: Path,
        backup_dir: Path,
        suffix: str = None
    ) -> Path:
        """
        Create backup of file or directory
        
        Args:
            path: Path to backup
            backup_dir: Directory to store backup
            suffix: Optional suffix for backup name
        
        Returns:
            Path to backup
        """
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            suffix = f"_{suffix}" if suffix else ""
            backup_name = f"{path.name}_{timestamp}{suffix}"
            backup_path = backup_dir / backup_name
            
            if path.is_file():
                shutil.copy2(path, backup_path)
            elif path.is_dir():
                shutil.copytree(path, backup_path)
            
            return backup_path
            
        except Exception as e:
            raise FileSystemError(f"Failed to create backup: {e}")
    
    @staticmethod
    def get_directory_size(path: Path) -> int:
        """Get total size of directory in bytes"""
        total = 0
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
        return total
    
    @staticmethod
    def ensure_directory(path: Path) -> bool:
        """Ensure directory exists, create if needed"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            raise FileSystemError(f"Failed to create directory {path}: {e}")


class ArchiveExtractor(LoggerMixin):
    """Extract archive files with validation"""
    
    @staticmethod
    def extract_zip(
        archive_path: Path,
        extract_to: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Path]:
        """
        Extract ZIP archive with progress tracking
        
        Args:
            archive_path: Path to ZIP file
            extract_to: Directory to extract to
            progress_callback: Optional callback(current, total, filename)
        
        Returns:
            List of extracted file paths
        
        Raises:
            ExtractionError: If extraction fails
        """
        extracted_files = []
        
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # Validate archive
                if zip_ref.testzip() is not None:
                    raise ExtractionError(f"Archive is corrupted: {archive_path}")
                
                members = zip_ref.namelist()
                total = len(members)
                
                for i, member in enumerate(members):
                    if progress_callback:
                        progress_callback(i + 1, total, member)
                    
                    # Security: Prevent path traversal
                    member_path = Path(member)
                    if any(part.startswith('..') for part in member_path.parts):
                        raise ExtractionError(f"Invalid archive member: {member}")
                    
                    # Extract
                    extracted_path = extract_to / member
                    zip_ref.extract(member, extract_to)
                    
                    if extracted_path.exists():
                        extracted_files.append(extracted_path)
            
            return extracted_files
            
        except zipfile.BadZipFile as e:
            raise ExtractionError(f"Invalid ZIP file: {e}")
        except Exception as e:
            raise ExtractionError(f"Extraction failed: {e}")
    
    @staticmethod
    def create_zip(
        source_path: Path,
        archive_path: Path,
        compression: int = zipfile.ZIP_DEFLATED,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Path:
        """
        Create ZIP archive from directory or file
        
        Args:
            source_path: Path to compress
            archive_path: Output ZIP file path
            compression: Compression method
            progress_callback: Optional callback(current, total, filename)
        
        Returns:
            Path to created archive
        """
        try:
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            
            if source_path.is_file():
                files = [source_path]
            else:
                files = list(source_path.rglob('*'))
                files = [f for f in files if f.is_file()]
            
            total = len(files)
            
            with zipfile.ZipFile(archive_path, 'w', compression) as zip_ref:
                for i, file_path in enumerate(files):
                    if progress_callback:
                        progress_callback(i + 1, total, file_path.name)
                    
                    arcname = file_path.relative_to(source_path.parent)
                    zip_ref.write(file_path, arcname)
            
            return archive_path
            
        except Exception as e:
            raise ExtractionError(f"Failed to create archive: {e}")


class TempDirectory:
    """Context manager for temporary directory"""
    
    def __init__(self, prefix: str = "valheim_mod_"):
        self.prefix = prefix
        self.path: Optional[Path] = None
    
    def __enter__(self) -> Path:
        self.path = Path(tempfile.mkdtemp(prefix=self.prefix))
        return self.path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.path and self.path.exists():
            try:
                shutil.rmtree(self.path)
            except Exception:
                pass  # Best effort cleanup


def safe_remove_directory(path: Path, max_retries: int = 3) -> bool:
    """
    Safely remove directory with retries
    
    Sometimes files are locked by Windows Explorer or other processes.
    This function retries removal with delays.
    """
    import time
    
    for attempt in range(max_retries):
        try:
            if not path.exists():
                return True
            
            shutil.rmtree(path)
            return True
            
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))  # Increasing delay
            else:
                return False
        except Exception:
            return False
    
    return False


def copy_with_progress(
    src: Path,
    dst: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> bool:
    """Convenience wrapper for FileOperations.copy_with_progress"""
    return FileOperations.copy_with_progress(src, dst, progress_callback)


def format_size(bytes_size: int) -> str:
    """Format bytes as human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def find_files_by_extension(
    directory: Path,
    extensions: List[str]
) -> List[Path]:
    """Find all files with given extensions in directory"""
    files = []
    for ext in extensions:
        if not ext.startswith('.'):
            ext = f'.{ext}'
        files.extend(directory.rglob(f'*{ext}'))
    return files


def is_path_inside(child: Path, parent: Path) -> bool:
    """Check if child path is inside parent path"""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
