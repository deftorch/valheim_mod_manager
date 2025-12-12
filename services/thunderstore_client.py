"""
Thunderstore API Client with Caching and Retry Logic
"""

import requests
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import Settings
from core.database import Database
from core.exceptions import APIError, DownloadError, TimeoutError, NetworkError
from utils.logger import LoggerMixin
from utils.file_utils import format_size


class ThunderstoreClient(LoggerMixin):
    """Client for Thunderstore API with caching and retry logic"""
    
    def __init__(self, database: Database = None):
        self.base_url = Settings.THUNDERSTORE_API_BASE
        self.community = Settings.THUNDERSTORE_COMMUNITY
        self.db = database or Database()
        self._cache = {}
        self._cache_timestamp = None
        
        # Setup session with retry
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'{Settings.APP_NAME}/{Settings.VERSION}'
        })
    
    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        if not self._cache_timestamp:
            return False
        
        age = datetime.now() - self._cache_timestamp
        max_age = timedelta(hours=Settings.CACHE_DURATION_HOURS)
        return age < max_age
    
    @retry(
        stop=stop_after_attempt(Settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=Settings.RETRY_BACKOFF, min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def _make_request(self, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic"""
        try:
            response = self.session.get(
                url,
                timeout=Settings.REQUEST_TIMEOUT,
                **kwargs
            )
            response.raise_for_status()
            return response
            
        except requests.Timeout:
            raise TimeoutError(f"Request timed out: {url}")
        except requests.RequestException as e:
            raise APIError(f"API request failed: {e}", getattr(e.response, 'status_code', None))
    
    def fetch_mods(self, force_refresh: bool = False) -> List[Dict]:
        """
        Fetch all mods from Thunderstore
        
        Args:
            force_refresh: Force refresh cache
        
        Returns:
            List of mod data dictionaries
        """
        # Check cache
        if not force_refresh and self._is_cache_valid() and self._cache:
            self.logger.info("Using cached mod list")
            return self._cache.get('mods', [])
        
        self.logger.info("Fetching mods from Thunderstore API")
        
        try:
            url = Settings.THUNDERSTORE_PACKAGES_URL
            response = self._make_request(url)
            data = response.json()
            
            # Parse and normalize data
            mods = []
            for package in data:
                try:
                    mod_data = self._parse_package(package)
                    if mod_data:
                        mods.append(mod_data)
                except Exception as e:
                    self.logger.warning(f"Failed to parse package: {e}")
                    continue
            
            # Update cache
            self._cache['mods'] = mods
            self._cache_timestamp = datetime.now()
            
            self.logger.info(f"Fetched {len(mods)} mods from Thunderstore")
            return mods
            
        except Exception as e:
            self.logger.error(f"Failed to fetch mods: {e}")
            # Return cached data if available
            if self._cache:
                self.logger.warning("Using stale cache due to error")
                return self._cache.get('mods', [])
            raise
    
    def _parse_package(self, package: Dict) -> Optional[Dict]:
        """Parse package data from API response"""
        try:
            # Get latest version
            versions = package.get('versions', [])
            if not versions:
                return None
            
            latest = versions[0]  # First version is latest
            
            return {
                'id': f"{package['owner']}-{package['name']}",
                'name': package.get('name', ''),
                'author': package.get('owner', ''),
                'version': latest.get('version_number', ''),
                'description': latest.get('description', ''),
                'full_description': package.get('full_description', ''),
                'download_url': latest.get('download_url', ''),
                'file_size': latest.get('file_size', 0),
                'rating': package.get('rating_score', 0.0),
                'downloads': latest.get('downloads', 0),
                'last_updated': latest.get('date_created', ''),
                'icon_url': latest.get('icon', ''),
                'website_url': package.get('package_url', ''),
                'dependencies': latest.get('dependencies', []),
                'categories': package.get('categories', []),
                'is_pinned': package.get('is_pinned', False),
                'is_deprecated': package.get('is_deprecated', False),
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to parse package: {e}")
            return None
    
    def search_mods(
        self,
        query: str = "",
        category: str = None,
        sort_by: str = "downloads",
        limit: int = Settings.MAX_SEARCH_RESULTS
    ) -> List[Dict]:
        """
        Search mods with filters
        
        Args:
            query: Search query
            category: Filter by category
            sort_by: Sort field ('downloads', 'rating', 'updated', 'name')
            limit: Maximum results
        
        Returns:
            List of matching mod data
        """
        mods = self.fetch_mods()
        
        # Apply text search
        if query:
            query_lower = query.lower()
            mods = [
                m for m in mods
                if query_lower in m['name'].lower() or
                   query_lower in m['author'].lower() or
                   query_lower in m['description'].lower()
            ]
        
        # Apply category filter
        if category:
            mods = [m for m in mods if category in m.get('categories', [])]
        
        # Apply sorting
        sort_key_map = {
            'downloads': lambda m: m.get('downloads', 0),
            'rating': lambda m: m.get('rating', 0.0),
            'updated': lambda m: m.get('last_updated', ''),
            'name': lambda m: m.get('name', '').lower(),
        }
        
        if sort_by in sort_key_map:
            mods.sort(key=sort_key_map[sort_by], reverse=True)
        
        return mods[:limit]
    
    def get_mod_details(self, mod_id: str) -> Optional[Dict]:
        """Get detailed information about a specific mod"""
        mods = self.fetch_mods()
        
        for mod in mods:
            if mod['id'] == mod_id:
                return mod
        
        return None
    
    def download_mod(
        self,
        mod_data: Dict,
        destination: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Path:
        """
        Download mod package
        
        Args:
            mod_data: Mod data dictionary
            destination: Directory to save download
            progress_callback: Optional callback(bytes_downloaded, total_bytes)
        
        Returns:
            Path to downloaded file
        
        Raises:
            DownloadError: If download fails
        """
        download_url = mod_data.get('download_url')
        if not download_url:
            raise DownloadError("No download URL available")
        
        mod_id = mod_data['id']
        version = mod_data['version']
        filename = f"{mod_id}-{version}.zip"
        output_path = destination / filename
        
        self.logger.info(f"Downloading {mod_id} v{version}")
        
        try:
            # Make request with stream
            response = self._make_request(download_url, stream=True)
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # Ensure destination directory exists
            destination.mkdir(parents=True, exist_ok=True)
            
            # Download with progress
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=Settings.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            progress_callback(downloaded, total_size)
            
            self.logger.info(
                f"Downloaded {filename} ({format_size(downloaded)})"
            )
            
            return output_path
            
        except Exception as e:
            # Cleanup partial download
            if output_path.exists():
                output_path.unlink()
            
            raise DownloadError(f"Download failed for {mod_id}: {e}")
    
    def download_icon(self, icon_url: str, destination: Path) -> Optional[Path]:
        """Download mod icon"""
        if not icon_url:
            return None
        
        try:
            response = self._make_request(icon_url)
            
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.content)
            
            return destination
            
        except Exception as e:
            self.logger.warning(f"Failed to download icon: {e}")
            return None
    
    def get_categories(self) -> List[str]:
        """Get list of available categories"""
        mods = self.fetch_mods()
        
        categories = set()
        for mod in mods:
            categories.update(mod.get('categories', []))
        
        return sorted(categories)
    
    def get_mod_dependencies(self, mod_data: Dict) -> List[Dict]:
        """
        Get dependency information for a mod
        
        Returns:
            List of dependency dictionaries with mod_id and version
        """
        dependencies = []
        
        for dep_string in mod_data.get('dependencies', []):
            try:
                # Format: "AuthorName-ModName-1.2.3"
                parts = dep_string.rsplit('-', 1)
                if len(parts) == 2:
                    mod_id = parts[0]
                    version = parts[1]
                    dependencies.append({
                        'mod_id': mod_id,
                        'version': version
                    })
            except Exception as e:
                self.logger.warning(f"Failed to parse dependency: {dep_string}")
        
        return dependencies
    
    def check_for_updates(self, installed_mods: Dict[str, str]) -> List[Dict]:
        """
        Check for available updates
        
        Args:
            installed_mods: Dict of mod_id -> current_version
        
        Returns:
            List of mods with updates available
        """
        updates = []
        available_mods = {m['id']: m for m in self.fetch_mods()}
        
        for mod_id, current_version in installed_mods.items():
            if mod_id in available_mods:
                latest = available_mods[mod_id]
                latest_version = latest['version']
                
                if self._compare_versions(latest_version, current_version) > 0:
                    updates.append({
                        'mod_id': mod_id,
                        'current_version': current_version,
                        'latest_version': latest_version,
                        'mod_data': latest
                    })
        
        return updates
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare semantic versions"""
        def normalize(v):
            try:
                return tuple(map(int, v.split('.')))
            except:
                return (0, 0, 0)
        
        v1_tuple = normalize(v1)
        v2_tuple = normalize(v2)
        
        if v1_tuple > v2_tuple:
            return 1
        elif v1_tuple < v2_tuple:
            return -1
        else:
            return 0
    
    def clear_cache(self):
        """Clear cached data"""
        self._cache.clear()
        self._cache_timestamp = None
        self.logger.info("Cache cleared")
