"""
Hash Calculation Utilities using xxHash for Fast Performance
"""

import xxhash
from pathlib import Path
from typing import Dict, Optional
from collections import OrderedDict

from config.settings import Settings


def calculate_file_hash(file_path: Path, algorithm: str = Settings.HASH_ALGORITHM) -> str:
    """
    Calculate hash of a file
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm ('xxhash64', 'md5', 'sha256')
    
    Returns:
        Hex digest of file hash
    """
    if not file_path.exists():
        return ""
    
    if algorithm == 'xxhash64':
        hasher = xxhash.xxh64()
    else:
        import hashlib
        hasher = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def calculate_directory_hash(directory: Path, algorithm: str = Settings.HASH_ALGORITHM) -> str:
    """
    Calculate combined hash of all files in directory
    
    Args:
        directory: Path to directory
        algorithm: Hash algorithm
    
    Returns:
        Hex digest of combined hash
    """
    if not directory.exists() or not directory.is_dir():
        return ""
    
    if algorithm == 'xxhash64':
        hasher = xxhash.xxh64()
    else:
        import hashlib
        hasher = hashlib.new(algorithm)
    
    # Sort files for consistent hashing
    files = sorted(directory.rglob('*'))
    
    for file_path in files:
        if file_path.is_file():
            # Include relative path in hash
            rel_path = file_path.relative_to(directory)
            hasher.update(str(rel_path).encode())
            
            # Include file content
            file_hash = calculate_file_hash(file_path, algorithm)
            hasher.update(file_hash.encode())
    
    return hasher.hexdigest()


def calculate_string_hash(data: str, algorithm: str = Settings.HASH_ALGORITHM) -> str:
    """Calculate hash of string data"""
    if algorithm == 'xxhash64':
        return xxhash.xxh64(data.encode()).hexdigest()
    else:
        import hashlib
        return hashlib.new(algorithm, data.encode()).hexdigest()


class HashCache:
    """
    LRU Cache for file hashes to avoid recalculation
    """
    
    def __init__(self, max_size: int = 1000):
        self.cache: OrderedDict[str, tuple] = OrderedDict()
        self.max_size = max_size
    
    def get(self, file_path: Path) -> Optional[str]:
        """
        Get cached hash for file
        
        Returns:
            Hash if cached and file unchanged, None otherwise
        """
        key = str(file_path.absolute())
        
        if key not in self.cache:
            return None
        
        # Check if file was modified since caching
        cached_hash, cached_mtime, cached_size = self.cache[key]
        
        try:
            stat = file_path.stat()
            if stat.st_mtime == cached_mtime and stat.st_size == cached_size:
                # Move to end (mark as recently used)
                self.cache.move_to_end(key)
                return cached_hash
        except (OSError, FileNotFoundError):
            # File no longer exists
            del self.cache[key]
            return None
        
        # File was modified, remove from cache
        del self.cache[key]
        return None
    
    def put(self, file_path: Path, file_hash: str):
        """Cache file hash with metadata"""
        key = str(file_path.absolute())
        
        try:
            stat = file_path.stat()
            self.cache[key] = (file_hash, stat.st_mtime, stat.st_size)
            
            # Move to end (mark as recently used)
            self.cache.move_to_end(key)
            
            # Enforce max size
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)  # Remove oldest
                
        except (OSError, FileNotFoundError):
            pass
    
    def calculate_or_get(self, file_path: Path) -> str:
        """Get cached hash or calculate and cache it"""
        cached = self.get(file_path)
        if cached:
            return cached
        
        file_hash = calculate_file_hash(file_path)
        self.put(file_path, file_hash)
        return file_hash
    
    def invalidate(self, file_path: Path):
        """Remove file from cache"""
        key = str(file_path.absolute())
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """Clear all cached hashes"""
        self.cache.clear()
    
    def size(self) -> int:
        """Get number of cached items"""
        return len(self.cache)


class FileHasher:
    """
    Utility for batch hash calculations with progress tracking
    """
    
    def __init__(self, cache: HashCache = None):
        self.cache = cache or HashCache()
    
    def hash_files(
        self,
        files: list[Path],
        progress_callback=None
    ) -> Dict[str, str]:
        """
        Calculate hashes for multiple files
        
        Args:
            files: List of file paths
            progress_callback: Optional callback(current, total, filename)
        
        Returns:
            Dict mapping file path to hash
        """
        result = {}
        total = len(files)
        
        for i, file_path in enumerate(files):
            if progress_callback:
                progress_callback(i + 1, total, file_path.name)
            
            file_hash = self.cache.calculate_or_get(file_path)
            result[str(file_path)] = file_hash
        
        return result
    
    def compare_directories(
        self,
        dir1: Path,
        dir2: Path
    ) -> tuple[set, set, set]:
        """
        Compare two directories by file hashes
        
        Returns:
            Tuple of (only_in_dir1, only_in_dir2, different_files)
        """
        files1 = {f.relative_to(dir1): f for f in dir1.rglob('*') if f.is_file()}
        files2 = {f.relative_to(dir2): f for f in dir2.rglob('*') if f.is_file()}
        
        only_in_dir1 = set(files1.keys()) - set(files2.keys())
        only_in_dir2 = set(files2.keys()) - set(files1.keys())
        
        common_files = set(files1.keys()) & set(files2.keys())
        different_files = set()
        
        for rel_path in common_files:
            hash1 = self.cache.calculate_or_get(files1[rel_path])
            hash2 = self.cache.calculate_or_get(files2[rel_path])
            
            if hash1 != hash2:
                different_files.add(rel_path)
        
        return only_in_dir1, only_in_dir2, different_files


def verify_file_integrity(file_path: Path, expected_hash: str) -> bool:
    """
    Verify file integrity against expected hash
    
    Args:
        file_path: Path to file
        expected_hash: Expected hash value
    
    Returns:
        True if hash matches, False otherwise
    """
    if not file_path.exists():
        return False
    
    actual_hash = calculate_file_hash(file_path)
    return actual_hash == expected_hash
