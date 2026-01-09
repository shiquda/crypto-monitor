"""
Update checker module using GitHub API.
"""

import logging

import requests
from PyQt6.QtCore import QThread, pyqtSignal


class UpdateChecker(QThread):
    """
    Worker thread to check for updates from GitHub Releases.
    """

    # Signals
    update_available = pyqtSignal(dict)  # release_info
    up_to_date = pyqtSignal(str)  # current_version
    check_failed = pyqtSignal(str)  # error_message

    GITHUB_API_URL = "https://api.github.com/repos/shiquda/crypto-monitor/releases/latest"

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self._logger = logging.getLogger(__name__)

    def run(self):
        """Execute the update check."""
        try:
            self._logger.info(f"Checking for updates... Current version: {self.current_version}")

            # 1. Fetch latest release
            response = requests.get(self.GITHUB_API_URL, timeout=10)

            if response.status_code != 200:
                self.check_failed.emit(f"GitHub API Error: {response.status_code}")
                return

            release_data = response.json()
            tag_name = release_data.get("tag_name", "")

            # 2. Parse version (remove 'v' prefix if present)
            latest_version = tag_name.lstrip("v")
            current = self.current_version.lstrip("v")

            self._logger.info(f"Latest version: {latest_version}")

            # 3. Compare versions
            # Simple lexicographical comparison works for standard semantic versioning (major.minor.patch)
            # For more complex cases, packaging.version is better, but let's keep dependencies low if possible.
            # However, "0.3.10" < "0.3.2" lexicographically is WRONG.
            # So we should split and compare integers.

            if self._is_newer(current, latest_version):
                self.update_available.emit(release_data)
            else:
                self.up_to_date.emit(self.current_version)

        except Exception as e:
            self._logger.error(f"Update check failed: {e}")
            self.check_failed.emit(str(e))

    def _is_newer(self, current: str, latest: str) -> bool:
        """
        Compare two version strings. Returns True if latest > current.
        Handles versions like "1.0.0", "v1.0.0", "1.0.0-beta".
        """
        try:
            # Normalize
            def parse(v):
                # Remove suffixes like -beta for simple comparison, or split properly
                # This is a basic implementation.
                parts = []
                for part in v.split("."):
                    # Extract numeric part
                    num = ""
                    for char in part:
                        if char.isdigit():
                            num += char
                        else:
                            break
                    parts.append(int(num) if num else 0)
                return parts

            curr_parts = parse(current)
            lat_parts = parse(latest)

            return lat_parts > curr_parts

        except Exception:
            # Fallback to string comparison if parsing fails
            return latest > current
