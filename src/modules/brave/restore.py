#!/usr/bin/env python3
"""
Brave Browser Data Restore

Restores bookmarks to Brave browser from previously exported data.
"""

import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Brave browser profile path in Linux
HOME = Path.home()
BRAVE_PATHS = {
    "linux": HOME / ".config/BraveSoftware/Brave-Browser",
}

# Backup directory from env or default
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

    return base_path


def get_available_exports() -> list[tuple[str, Path]]:
    """Get list of available profile exports.

    Returns:
        List of tuples containing (profile_name, export_path)
    """
    if not EXPORT_DIR.exists():
        return []

    profiles = []

    for item in EXPORT_DIR.iterdir():
        if item.is_dir():
            profiles.append((item.name, item))

    # Sort: Default first, then alphabetically
    profiles.sort(key=lambda x: (x[0] != "Default", x[0]))

    return profiles


def get_existing_brave_profiles() -> list[tuple[str, Path]]:
    """Find existing Brave browser profiles.

    Returns:
        List of tuples containing (profile_name, profile_path)
    """
    base_path = get_brave_base_path()

    if not base_path or not base_path.exists():
        return []

    profiles = []

    for item in base_path.iterdir():
        if not item.is_dir():
            continue

        # Check if this looks like a profile directory
        if item.name.startswith("Profile") or item.name == "Default":
            profile_name = item.name

            # Try to get profile name from Preferences
            prefs_file = item / "Preferences"
            if prefs_file.exists():
                try:
                    with open(prefs_file, "r", encoding="utf-8") as f:
                        prefs = json.load(f)
                        profile_info = prefs.get("profile", {})
                        name = profile_info.get("name", "")
                        if name:
                            profile_name = f"{item.name} ({name})"
                except (json.JSONDecodeError, KeyError):
                    pass

            profiles.append((profile_name, item))

    # Sort: Default first, then alphabetically
    profiles.sort(key=lambda x: (x[1].name != "Default", x[1].name))

    return profiles


class BraveDataRestore:
    """Restores bookmarks to Brave browser."""

    def __init__(self, export_path: Path, target_path: Path):
        self.export_path = export_path
        self.target_path = target_path

    def restore_bookmarks(self, backup: bool = True) -> bool:
        """Restore bookmarks to Brave profile.

        First tries to restore from raw Bookmarks file, falls back to
        reconstructing from bookmarks.json.
        """
        # Try raw Bookmarks file first (if extract was updated to save it)
        raw_bookmarks = self.export_path / "Bookmarks"
        if raw_bookmarks.exists():
            return self._restore_raw_bookmarks(raw_bookmarks, backup)

        # Fall back to reconstructing from JSON
        json_bookmarks = self.export_path / "bookmarks.json"
        if json_bookmarks.exists():
            return self._restore_from_json(json_bookmarks, backup)

        print("    ⚠️  No bookmarks found in export")
        return False

    def _restore_raw_bookmarks(self, source: Path, backup: bool) -> bool:
        """Restore from raw Bookmarks file."""
        target = self.target_path / "Bookmarks"

        # Backup existing bookmarks
        if backup and target.exists():
            backup_path = target.with_suffix(".bak")
            shutil.copy2(target, backup_path)
            print(f"    📦 Backed up existing bookmarks to: {backup_path.name}")

        try:
            shutil.copy2(source, target)
            print("    ✅ Restored bookmarks from raw Bookmarks file")
            return True
        except Exception as e:
            print(f"    ❌ Error restoring bookmarks: {e}")
            return False

    def _restore_from_json(self, source: Path, backup: bool) -> bool:
        """Restore from exported bookmarks.json by reconstructing Brave format."""
        target = self.target_path / "Bookmarks"

        # Backup existing bookmarks
        if backup and target.exists():
            backup_path = target.with_suffix(".bak")
            shutil.copy2(target, backup_path)
            print(f"    📦 Backed up existing bookmarks to: {backup_path.name}")

        try:
            with open(source, "r", encoding="utf-8") as f:
                exported_bookmarks = json.load(f)

            # Reconstruct Brave bookmarks format
            brave_bookmarks = self._reconstruct_brave_format(exported_bookmarks)

            with open(target, "w", encoding="utf-8") as f:
                json.dump(brave_bookmarks, f, indent=3)

            print("    ✅ Restored bookmarks from bookmarks.json")
            return True
        except Exception as e:
            print(f"    ❌ Error restoring bookmarks: {e}")
            return False

    def _reconstruct_brave_format(self, exported: list) -> dict:
        """Reconstruct Brave's bookmarks format from exported data."""
        import time

        # Current timestamp in Chrome format (microseconds since 1601-01-01)
        chrome_epoch = 11644473600000000  # Microseconds between 1601 and 1970
        current_timestamp = str(int(time.time() * 1000000) + chrome_epoch)

        def convert_to_brave_node(item: dict, id_counter: list) -> dict:
            """Convert exported bookmark item to Brave format."""
            node_id = str(id_counter[0])
            id_counter[0] += 1

            if item.get("type") == "bookmark":
                return {
                    "date_added": current_timestamp,
                    "date_last_used": "0",
                    "guid": "",
                    "id": node_id,
                    "name": item.get("name", ""),
                    "type": "url",
                    "url": item.get("url", ""),
                }
            elif item.get("type") == "folder":
                children = [
                    convert_to_brave_node(child, id_counter)
                    for child in item.get("children", [])
                ]
                return {
                    "children": children,
                    "date_added": current_timestamp,
                    "date_last_used": "0",
                    "date_modified": current_timestamp,
                    "guid": "",
                    "id": node_id,
                    "name": item.get("name", ""),
                    "type": "folder",
                }
            return {}

        # Find bookmark_bar, other, and synced folders from exported data
        bookmark_bar_children = []
        other_children = []

        id_counter = [1]

        for item in exported:
            if item.get("type") == "folder":
                name = item.get("name", "").lower()
                if "bookmark" in name and "bar" in name:
                    bookmark_bar_children = [
                        convert_to_brave_node(child, id_counter)
                        for child in item.get("children", [])
                    ]
                elif name in ["other", "other bookmarks"]:
                    other_children = [
                        convert_to_brave_node(child, id_counter)
                        for child in item.get("children", [])
                    ]
                else:
                    # Add other folders to bookmark bar
                    bookmark_bar_children.append(
                        convert_to_brave_node(item, id_counter)
                    )

        return {
            "checksum": "",
            "roots": {
                "bookmark_bar": {
                    "children": bookmark_bar_children,
                    "date_added": current_timestamp,
                    "date_last_used": "0",
                    "date_modified": current_timestamp,
                    "guid": "00000000-0000-4000-a000-000000000002",
                    "id": "1",
                    "name": "Bookmarks bar",
                    "type": "folder",
                },
                "other": {
                    "children": other_children,
                    "date_added": current_timestamp,
                    "date_last_used": "0",
                    "date_modified": current_timestamp,
                    "guid": "00000000-0000-4000-a000-000000000003",
                    "id": "2",
                    "name": "Other bookmarks",
                    "type": "folder",
                },
                "synced": {
                    "children": [],
                    "date_added": current_timestamp,
                    "date_last_used": "0",
                    "date_modified": current_timestamp,
                    "guid": "00000000-0000-4000-a000-000000000004",
                    "id": "3",
                    "name": "Mobile bookmarks",
                    "type": "folder",
                },
            },
            "version": 1,
        }

    def restore_history(self, backup: bool = True) -> bool:
        """Restore history database to Brave profile."""
        source = self.export_path / "History"

        if not source.exists():
            print("    ⚠️  No History file found in backup")
            return False

        target = self.target_path / "History"

        # Backup existing history
        if backup and target.exists():
            backup_path = target.with_suffix(".bak")
            shutil.copy2(target, backup_path)
            print(f"    📦 Backed up existing history to: {backup_path.name}")

        try:
            shutil.copy2(source, target)
            print("    ✅ Restored history database")
            return True
        except Exception as e:
            print(f"    ❌ Error restoring history: {e}")
            return False

    def show_html_import_instructions(self):
        """Show instructions for manually importing bookmarks from HTML."""
        html_file = self.export_path / "bookmarks.html"

        if not html_file.exists():
            return

        print("\n    💡 Alternative: Import from HTML file")
        print("    ─" * 25)
        print(f"    HTML file: {html_file}")
        print("\n    To import manually in Brave:")
        print("    1. Open Brave browser")
        print("    2. Go to brave://settings/importData")
        print("    3. Select 'Bookmarks HTML File' from dropdown")
        print("    4. Click 'Choose File' and select the HTML file above")
        print("    5. Click 'Import'")


def restore_profile(
    export_name: str,
    export_path: Path,
    target_path: Path,
) -> dict:
    """Restore data to a single profile."""
    print(f"\n{'─' * 50}")
    print(f"📁 Restoring: {export_name}")
    print(f"   From: {export_path}")
    print(f"   To: {target_path}")
    print(f"{'─' * 50}")

    # Check if target profile exists
    if not target_path.exists():
        print(f"\n    ⚠️  Target profile doesn't exist: {target_path}")
        print("    Creating profile directory...")
        target_path.mkdir(parents=True, exist_ok=True)

    restorer = BraveDataRestore(export_path, target_path)

    # Restore bookmarks
    print("\n  🔖 Restoring bookmarks...")
    bookmarks_ok = restorer.restore_bookmarks(backup=True)

    if not bookmarks_ok:
        restorer.show_html_import_instructions()

    # Restore history
    print("\n  📜 Restoring history...")
    history_ok = restorer.restore_history(backup=True)

    return {
        "profile": export_name,
        "bookmarks_restored": bookmarks_ok,
        "history_restored": history_ok,
    }


def select_target_profile(exports: list, existing_profiles: list) -> dict:
    """Map export profiles to target profiles."""
    mapping = {}

    print("\n📋 Profile Mapping")
    print("─" * 50)

    for export_name, export_path in exports:
        # Try to find matching profile
        target = None

        for profile_name, profile_path in existing_profiles:
            if profile_path.name == export_name:
                target = profile_path
                break

        if target:
            print(f"  ✓ {export_name} → {target}")
        else:
            # Default to creating in the standard location
            base_path = get_brave_base_path()
            target = base_path / export_name
            print(f"  ? {export_name} → {target} (will create)")

        mapping[export_name] = (export_path, target)

    return mapping


def main():
    """Main entry point."""
    print("=" * 50)
    print("🦁 Brave Browser Data Restore")
    print("=" * 50)

    # Check for exports
    exports = get_available_exports()

    if not exports:
        print(f"\n❌ No exports found in: {EXPORT_DIR}")
        print("\nRun the extract script first to create a backup.")
        sys.exit(1)

    print(f"\n✅ Found {len(exports)} export(s):")
    for name, path in exports:
        print(f"   • {name}")

    # Check Brave installation
    base_path = get_brave_base_path()
    if not base_path:
        print("\n❌ Brave browser path not found!")
        sys.exit(1)

    # Get existing profiles
    existing_profiles = get_existing_brave_profiles()

    if existing_profiles:
        print(f"\n✅ Found {len(existing_profiles)} existing Brave profile(s):")
        for name, path in existing_profiles:
            print(f"   • {name}")
    else:
        print("\n⚠️  No existing Brave profiles found (fresh install)")
        print(f"   Will create profiles in: {base_path}")

    # Map exports to targets
    mapping = select_target_profile(exports, existing_profiles)

    # Confirm restore
    print("\n" + "=" * 50)
    print("⚠️  WARNING: This will modify your Brave browser data!")
    print("   Existing bookmarks and history will be backed up.")
    print("   Make sure Brave is CLOSED before proceeding!")
    print("=" * 50)

    response = input("\nProceed with restore? [y/N]: ").strip().lower()
    if response != "y":
        print("\n❌ Restore cancelled.")
        sys.exit(0)

    # Perform restore
    results = []
    for export_name, (export_path, target_path) in mapping.items():
        result = restore_profile(export_name, export_path, target_path)
        results.append(result)

    # Print summary
    print(f"\n{'=' * 50}")
    print("📊 Restore Summary")
    print(f"{'=' * 50}")

    for result in results:
        bookmarks_status = "✅" if result["bookmarks_restored"] else "❌"
        history_status = "✅" if result["history_restored"] else "❌"
        print(f"\n  {result['profile']}:")
        print(f"    • Bookmarks: {bookmarks_status}")
        print(f"    • History: {history_status}")

    print(f"\n{'=' * 50}")
    print("✨ Restore complete!")
    print("\n⚠️  Please restart Brave browser to see the restored data.")
    print("=" * 50)


if __name__ == "__main__":
    main()
