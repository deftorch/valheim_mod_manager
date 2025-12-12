"""
Game Launcher for Starting Valheim
"""

import subprocess
import platform
from pathlib import Path
from typing import Optional
import time

from core.exceptions import GamePathInvalidError
from utils.logger import LoggerMixin
from config.settings import Settings


class GameLauncher(LoggerMixin):
    """Handles launching Valheim game"""
    
    def __init__(self):
        self.system = platform.system()
        self.game_process: Optional[subprocess.Popen] = None
    
    def find_game_path(self) -> Optional[Path]:
        """
        Auto-detect Valheim installation path
        
        Returns:
            Path to Valheim directory or None if not found
        """
        self.logger.info("Searching for Valheim installation...")
        
        for path in Settings.get_default_game_paths():
            if self.validate_game_path(path, silent=True):
                self.logger.info(f"Found Valheim at: {path}")
                return path
        
        self.logger.warning("Valheim installation not found")
        return None
    
    def validate_game_path(self, game_path: Path, silent: bool = False) -> bool:
        """
        Validate that path contains Valheim installation
        
        Args:
            game_path: Path to check
            silent: If True, don't log errors
        
        Returns:
            True if valid Valheim directory
        """
        if not game_path.exists():
            if not silent:
                self.logger.error(f"Game path does not exist: {game_path}")
            return False
        
        # Check for game executable
        exe_names = self._get_executable_names()
        has_exe = any((game_path / exe).exists() for exe in exe_names)
        
        if not has_exe:
            if not silent:
                self.logger.error(f"Game executable not found in: {game_path}")
            return False
        
        return True
    
    def _get_executable_names(self) -> list[str]:
        """Get list of possible executable names for current platform"""
        if self.system == "Windows":
            return ['valheim.exe']
        elif self.system == "Linux":
            return ['valheim', 'valheim.x86_64']
        elif self.system == "Darwin":  # macOS
            return ['valheim', 'Valheim.app/Contents/MacOS/valheim']
        return ['valheim']
    
    def launch_game(
        self,
        game_path: Path,
        args: list[str] = None,
        wait: bool = False
    ) -> bool:
        """
        Launch Valheim game
        
        Args:
            game_path: Path to Valheim directory
            args: Optional command line arguments
            wait: If True, wait for game to exit
        
        Returns:
            True if launched successfully
        
        Raises:
            GamePathInvalidError: If game path is invalid
        """
        if not self.validate_game_path(game_path):
            raise GamePathInvalidError(f"Invalid game path: {game_path}")
        
        # Find executable
        exe_path = self._find_executable(game_path)
        if not exe_path:
            raise GamePathInvalidError(f"Game executable not found in: {game_path}")
        
        self.logger.info(f"Launching Valheim: {exe_path}")
        
        try:
            # Build command
            cmd = [str(exe_path)]
            if args:
                cmd.extend(args)
            
            # Launch process
            if self.system == "Windows":
                # On Windows, use CREATE_NEW_CONSOLE to detach
                self.game_process = subprocess.Popen(
                    cmd,
                    cwd=str(game_path),
                    creationflags=subprocess.CREATE_NEW_CONSOLE if not wait else 0
                )
            else:
                # On Unix-like systems
                self.game_process = subprocess.Popen(
                    cmd,
                    cwd=str(game_path),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # Wait a moment to check if process started successfully
            time.sleep(1)
            
            if self.game_process.poll() is not None:
                # Process exited immediately, probably failed
                self.logger.error("Game process exited immediately")
                return False
            
            self.logger.info(f"Game launched successfully (PID: {self.game_process.pid})")
            
            if wait:
                self.logger.info("Waiting for game to exit...")
                self.game_process.wait()
                self.logger.info("Game exited")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to launch game: {e}")
            return False
    
    def _find_executable(self, game_path: Path) -> Optional[Path]:
        """Find game executable in directory"""
        for exe_name in self._get_executable_names():
            exe_path = game_path / exe_name
            if exe_path.exists():
                return exe_path
        return None
    
    def launch_steam(self, game_path: Path = None) -> bool:
        """
        Launch Valheim through Steam
        
        This is more reliable as Steam handles game initialization
        
        Args:
            game_path: Optional game path (not used, for compatibility)
        
        Returns:
            True if launched successfully
        """
        # Valheim Steam App ID
        VALHEIM_APP_ID = "892970"
        
        try:
            if self.system == "Windows":
                steam_cmd = f"steam://run/{VALHEIM_APP_ID}"
                subprocess.Popen(['cmd', '/c', 'start', steam_cmd])
            
            elif self.system == "Linux":
                steam_cmd = f"steam://run/{VALHEIM_APP_ID}"
                subprocess.Popen(['xdg-open', steam_cmd])
            
            elif self.system == "Darwin":  # macOS
                steam_cmd = f"steam://run/{VALHEIM_APP_ID}"
                subprocess.Popen(['open', steam_cmd])
            
            else:
                self.logger.error(f"Unsupported platform: {self.system}")
                return False
            
            self.logger.info("Launched Valheim through Steam")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to launch through Steam: {e}")
            return False
    
    def is_game_running(self) -> bool:
        """Check if game is currently running"""
        if self.game_process:
            return self.game_process.poll() is None
        
        # Check system processes
        return self._check_game_process()
    
    def _check_game_process(self) -> bool:
        """Check if Valheim process is running in system"""
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq valheim.exe'],
                    capture_output=True,
                    text=True
                )
                return 'valheim.exe' in result.stdout.lower()
            
            else:
                result = subprocess.run(
                    ['pgrep', '-x', 'valheim'],
                    capture_output=True
                )
                return result.returncode == 0
                
        except Exception:
            return False
    
    def terminate_game(self) -> bool:
        """Terminate running game process"""
        if not self.game_process:
            return False
        
        try:
            self.game_process.terminate()
            self.game_process.wait(timeout=10)
            self.logger.info("Game process terminated")
            return True
        except subprocess.TimeoutExpired:
            # Force kill if terminate didn't work
            self.game_process.kill()
            self.logger.warning("Game process killed (force)")
            return True
        except Exception as e:
            self.logger.error(f"Failed to terminate game: {e}")
            return False
    
    def get_launch_options(self, game_path: Path) -> dict:
        """
        Get available launch options for game
        
        Returns:
            Dict of option_name -> description
        """
        return {
            'console': 'Enable debug console (F5)',
            'skipintro': 'Skip intro video',
            'windowed': 'Run in windowed mode',
            'popupwindow': 'Run in borderless windowed mode',
            'screen-width': 'Set screen width (e.g., -screen-width 1920)',
            'screen-height': 'Set screen height (e.g., -screen-height 1080)',
        }
    
    def build_launch_args(self, options: dict) -> list[str]:
        """
        Build command line arguments from options
        
        Args:
            options: Dict of option -> value (True for flags, str for valued options)
        
        Returns:
            List of command line arguments
        """
        args = []
        
        for option, value in options.items():
            if value is True:
                args.append(f'-{option}')
            elif isinstance(value, str):
                args.append(f'-{option}')
                args.append(value)
            elif isinstance(value, (int, float)):
                args.append(f'-{option}')
                args.append(str(value))
        
        return args
