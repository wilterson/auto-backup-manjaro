#!/usr/bin/env python3
"""
Brave Browser Data Extractor

Extracts bookmarks from Brave browser for backup and restore.
Supports multiple profiles.
"""

import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Brave browser profile path in linux
HOME = Path.home()
BRAVE_PATHS = {
    "linux": HOME / ".config/BraveSoftware/Brave-Browser",
}

# Output directory from env or default
BACKUP_FOLDER_PATH = os.getenv("BACKUP_FOLDER_PATH", "")
EXPORT_DIR = Path(f"{BACKUP_FOLDER_PATH}/brave-data/")


def get_brave_base_path() -> Path | None:
    """Get the Brave browser base path for the current OS."""
    platform = sys.platform

    if platform.startswith("linux"):
        base_path = BRAVE_PATHS["linux"]
    else:
        print(f"❌ Unsupported platform: {platform}")
        return None

    if base_path.exists():
        return base_path

    return None


def get_all_brave_profiles() -> list[tuple[str, Path]]:
    """Find all Brave browser profiles.

    Returns:
        List of tuples containing (profile_name, profile_path)
    """
    base_path = get_brave_base_path()

    if not base_path:
        return []

    profiles = []

    for item in base_path.iterdir():
        if not item.is_dir():
            continue

        # Check if this directory contains browser data (History or Bookmarks file)
        has_history = (item / "History").exists()
        has_bookmarks = (item / "Bookmarks").exists()

        if has_history or has_bookmarks:
            # Get profile name from Preferences file if available
            profile_name = item.name
            prefs_file = item / "Preferences"

            if prefs_file.exists():
                try:
                    with open(prefs_file, "r", encoding="utf-8") as f:
                        prefs = json.load(f)
                        # Try to get the profile name from preferences
                        account_info = prefs.get("account_info", [])
                        if account_info and isinstance(account_info, list):
                            email = account_info[0].get("email", "")
                            if email:
                                profile_name = f"{item.name} ({email})"
                        else:
                            profile_info = prefs.get("profile", {})
                            name = profile_info.get("name", "")
                            if name:
                                profile_name = f"{item.name} ({name})"
                except (json.JSONDecodeError, KeyError):
                    pass

            profiles.append((profile_name, item))

    # Sort profiles: Default first, then alphabetically
    profiles.sort(key=lambda x: (x[1].name != "Default", x[1].name))

    return profiles


def chromium_timestamp_to_datetime(timestamp: int) -> datetime:
    """Convert Chromium timestamp (microseconds since 1601-01-01) to datetime."""
    # Chromium epoch starts at 1601-01-01
    epoch_start = datetime(1601, 1, 1)
    return epoch_start + timedelta(microseconds=timestamp)


class BraveDataExtractor:
    """Extracts bookmarks from Brave browser."""

    def __init__(self, profile_path: Path, output_dir: Path):
        self.profile_path = profile_path
        self.output_dir = output_dir

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_bookmarks(self) -> list[dict]:
        """Extract bookmarks from Brave."""
        bookmarks_file = self.profile_path / "Bookmarks"

        if not bookmarks_file.exists():
            print("    ⚠️  Bookmarks file not found")
            return []

        with open(bookmarks_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        bookmarks = self._parse_bookmarks_recursive(data.get("roots", {}))
        total = self.count_bookmarks(bookmarks)
        print(f"    ✅ Extracted {total} bookmarks")
        return bookmarks

    def _parse_bookmarks_recursive(self, node: dict) -> list[dict]:
        """Recursively parse bookmark nodes."""
        bookmarks = []

        for key, value in node.items():
            if isinstance(value, dict):
                if value.get("type") == "url":
                    bookmarks.append(
                        {
                            "type": "bookmark",
                            "name": value.get("name", ""),
                            "url": value.get("url", ""),
                            "date_added": self._parse_chrome_date(
                                value.get("date_added")
                            ),
                        }
                    )
                elif value.get("type") == "folder":
                    children = value.get("children", [])
                    bookmarks.append(
                        {
                            "type": "folder",
                            "name": value.get("name", key),
                            "children": self._parse_children(children),
                        }
                    )
                elif "children" in value:
                    # Root folders like bookmark_bar, other, synced
                    bookmarks.append(
                        {
                            "type": "folder",
                            "name": value.get("name", key),
                            "children": self._parse_children(value.get("children", [])),
                        }
                    )

        return bookmarks

    def _parse_children(self, children: list) -> list[dict]:
        """Parse bookmark children array."""
        result = []

        for child in children:
            if child.get("type") == "url":
                result.append(
                    {
                        "type": "bookmark",
                        "name": child.get("name", ""),
                        "url": child.get("url", ""),
                        "date_added": self._parse_chrome_date(child.get("date_added")),
                    }
                )
            elif child.get("type") == "folder":
                result.append(
                    {
                        "type": "folder",
                        "name": child.get("name", ""),
                        "children": self._parse_children(child.get("children", [])),
                    }
                )

        return result

    def _parse_chrome_date(self, timestamp_str: str) -> str:
        """Parse Chrome/Brave timestamp string to readable date."""
        if not timestamp_str:
            return "Unknown"
        try:
            timestamp = int(timestamp_str)
            dt = chromium_timestamp_to_datetime(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return "Unknown"

    def count_bookmarks(self, bookmarks: list) -> int:
        """Count total bookmarks recursively."""
        count = 0
        for item in bookmarks:
            if item.get("type") == "bookmark":
                count += 1
            elif item.get("type") == "folder":
                count += self.count_bookmarks(item.get("children", []))
        return count

    def export_bookmarks_json(
        self, bookmarks: list[dict], filename: str = "bookmarks.json"
    ):
        """Export bookmarks to JSON file (fallback for restore)."""
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(bookmarks, f, indent=2, ensure_ascii=False)
        print(f"    📄 Bookmarks JSON exported to: {output_path}")

    def copy_raw_bookmarks(self) -> bool:
        """Copy the raw Bookmarks file for exact restoration."""
        bookmarks_file = self.profile_path / "Bookmarks"

        if not bookmarks_file.exists():
            return False

        try:
            shutil.copy2(bookmarks_file, self.output_dir / "Bookmarks")
            print(f"    📄 Raw Bookmarks copied for restore")
            return True
        except Exception as e:
            print(f"    ⚠️  Could not copy raw Bookmarks: {e}")
            return False

    def copy_raw_history(self) -> bool:
        """Copy the raw History database for exact restoration."""
        history_file = self.profile_path / "History"

        if not history_file.exists():
            print("    ⚠️  History file not found")
            return False

        try:
            shutil.copy2(history_file, self.output_dir / "History")
            # Get file size for info
            size_mb = history_file.stat().st_size / (1024 * 1024)
            print(f"    📄 History database copied ({size_mb:.1f} MB)")
            return True
        except Exception as e:
            print(f"    ⚠️  Could not copy History: {e}")
            return False


def export_profile(profile_name: str, profile_path: Path, base_output_dir: Path):
    """Export data from a single profile."""
    # Create a safe folder name from the profile name
    safe_name = profile_path.name  # Use the directory name (Default, Profile 1, etc.)
    profile_output_dir = base_output_dir / safe_name

    print(f"\n{'─' * 50}")
    print(f"📁 Profile: {profile_name}")
    print(f"   Path: {profile_path}")
    print(f"   Output: {profile_output_dir}")
    print(f"{'─' * 50}")

    extractor = BraveDataExtractor(profile_path, profile_output_dir)

    # Extract bookmarks
    print("\n  🔖 Extracting bookmarks...")
    bookmarks = extractor.extract_bookmarks()
    bookmarks_ok = False
    if bookmarks:
        bookmarks_ok = extractor.copy_raw_bookmarks()
        extractor.export_bookmarks_json(bookmarks)  # Fallback

    # Extract history
    print("\n  📜 Extracting history...")
    history_ok = extractor.copy_raw_history()

    return {
        "profile": profile_name,
        "bookmarks_count": extractor.count_bookmarks(bookmarks) if bookmarks else 0,
        "history_ok": history_ok,
        "bookmarks_ok": bookmarks_ok,
    }


def main():
    """Main entry point."""
    print("=" * 50)
    print("🦁 Brave Browser Data Extractor")
    print("=" * 50)

    # Find all profiles
    profiles = get_all_brave_profiles()

    if not profiles:
        print("\n❌ No Brave browser profiles found!")
        print("\nExpected location:")
        for os_name, path in BRAVE_PATHS.items():
            print(f"  {os_name}: {path}")
        sys.exit(1)

    print(f"\n✅ Found {len(profiles)} profile(s):")
    for name, path in profiles:
        print(f"   • {name}")

    # Export each profile
    results = []
    for profile_name, profile_path in profiles:
        result = export_profile(profile_name, profile_path, EXPORT_DIR)
        results.append(result)

    # Print summary
    print(f"\n{'=' * 50}")
    print("📊 Export Summary")
    print(f"{'=' * 50}")

    total_bookmarks = 0

    for result in results:
        print(f"\n  {result['profile']}:")
        print(
            f"    • Bookmarks: {result['bookmarks_count']} {'✅' if result['bookmarks_ok'] else '❌'}"
        )
        print(f"    • History: {'✅' if result['history_ok'] else '❌'}")
        total_bookmarks += result["bookmarks_count"]

    print(f"\n  {'─' * 40}")
    print(f"  Total: {total_bookmarks} bookmarks")
    print(f"\n✨ All exports saved to: {EXPORT_DIR.absolute()}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
