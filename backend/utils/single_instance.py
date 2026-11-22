"""Single-instance enforcement using Windows named mutex or file lock.
Prevents multiple instances from running concurrently and conflicting over ports and SQLite DB.
"""
from __future__ import annotations

import os
import sys
from config import LOCK_FILE_PATH
from utils.logging_config import logger

class SingleInstance:
    def __init__(self):
        self.lock_file = LOCK_FILE_PATH
        self.lock_fd = None
        self._win_mutex = None

    def acquire(self) -> bool:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            mutex_name = "Local\\AutoSocialPoster_SingleInstance_Mutex"
            
            # CreateMutexW(security_attributes, initial_owner, name)
            self._win_mutex = kernel32.CreateMutexW(None, False, mutex_name)
            last_error = ctypes.get_last_error()
            ERROR_ALREADY_EXISTS = 183

            if last_error == ERROR_ALREADY_EXISTS:
                logger.warning("Another instance of AutoSocial Poster is already running.")
                return False
            return True
        else:
            try:
                import fcntl
                self.lock_fd = open(self.lock_file, "w")
                fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except (IOError, OSError):
                return False

    def release(self):
        if os.name == "nt" and self._win_mutex:
            import ctypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle(self._win_mutex)
            self._win_mutex = None
        elif self.lock_fd:
            try:
                import fcntl
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
            except Exception:
                pass
