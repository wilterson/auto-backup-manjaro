#!/usr/bin/env python3
"""
Cursor IDE Data Restore

Restores settings, keybindings, snippets, and extensions to Cursor IDE
from previously exported data.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Cursor IDE paths in Linux
HOME = Path.home()
CURSOR_PATHS = {
    "config": HOME / ".config/Cursor",
    "data": HOME / ".cursor",
}

# Export directory from env or default
BACKUP_FOLDER_PATH = os.getenv("BACKUP_FOLDER_PATH", "")
EXPORT_DIR = Path(f"{BACKUP_FOLDER_PATH}/cursor-data/")

# Cursor executable name
CURSOR_CMD = os.getenv("CURSOR_EXECUTABLE", "cursor")


def get_cursor_paths() -> dict | None:
    """Get Cursor IDE paths for the current system."""
    config_path = CURSOR_PATHS["config"]
    data_path = CURSOR_PATHS["data"]

    return {
        "config": config_path,
        "data": data_path,
        "user": config_path / "User",
        "extensions": data_path / "extensions",
    }


def check_cursor_installed() -> bool:
    """Check if Cursor is installed and accessible."""
    try:
        result = subprocess.run(
            [CURSOR_CMD, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_available_exports() -> list[tuple[str, Path, bool]]:
    """Get list of available profile exports.

    Returns:
        List of tuples containing (profile_name, export_path, is_default)
    """
    if not EXPORT_DIR.exists():
        return []

    profiles = []

    for item in EXPORT_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            is_default = item.name == "Default"
            profiles.append((item.name, item, is_default))

    # Sort: Default first, then alphabetically
    profiles.sort(key=lambda x: (not x[2], x[0]))

    return profiles


class CursorDataRestore:
    """Restores settings, keybindings, snippets, and extensions to Cursor IDE."""

    def __init__(self, export_path: Path, target_path: Path, is_default: bool = False):
        self.export_path = export_path
        self.target_path = target_path
        self.is_default = is_default

    def restore_settings(self, merge: bool = False) -> bool:
        """Restore settings.json to Cursor."""
        source = self.export_path / "settings.json"

        if not source.exists():
            print("    ⚠️  No settings.json found in export")
            return False

        target = self.target_path / "settings.json"

        try:
            if merge and target.exists():
                # Merge settings
                with open(target, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                with open(source, "r", encoding="utf-8") as f:
                    exported = json.load(f)

                # Exported settings take precedence
                merged = {**existing, **exported}

                with open(target, "w", encoding="utf-8") as f:
                    json.dump(merged, f, indent=2, ensure_ascii=False)

                print(f"    ✅ Merged {len(exported)} settings into existing config")
            else:
                # Backup existing if present
                if target.exists():
                    backup = target.with_suffix(".json.backup")
                    shutil.copy2(target, backup)
                    print(f"    📦 Backed up existing settings to {backup.name}")

                # Copy new settings
                self.target_path.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                print(f"    ✅ Restored settings.json")

            return True

        except Exception as e:
            print(f"    ❌ Error restoring settings: {e}")
            return False

    def restore_keybindings(self) -> bool:
        """Restore keybindings.json to Cursor."""
        source = self.export_path / "keybindings.json"

        if not source.exists():
            print("    ⚠️  No keybindings.json found in export")
            return False

        target = self.target_path / "keybindings.json"

        try:
            # Backup existing if present
            if target.exists():
                backup = target.with_suffix(".json.backup")
                shutil.copy2(target, backup)
                print(f"    📦 Backed up existing keybindings to {backup.name}")

            # Copy new keybindings
            self.target_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            print(f"    ✅ Restored keybindings.json")
            return True

        except Exception as e:
            print(f"    ❌ Error restoring keybindings: {e}")
            return False

    def restore_snippets(self) -> bool:
        """Restore snippets to Cursor."""
        source_dir = self.export_path / "snippets"

        if not source_dir.exists():
            print("    ⚠️  No snippets directory found in export")
            return False

        target_dir = self.target_path / "snippets"

        try:
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)

            copied = 0
            for snippet_file in source_dir.glob("*.json"):
                target_file = target_dir / snippet_file.name

                # Backup existing if present
                if target_file.exists():
                    backup = target_file.with_suffix(".json.backup")
                    shutil.copy2(target_file, backup)

                shutil.copy2(snippet_file, target_file)
                copied += 1

            print(f"    ✅ Restored {copied} snippet files")
            return True

        except Exception as e:
            print(f"    ❌ Error restoring snippets: {e}")
            return False

    def get_extensions_to_install(self) -> list[str]:
        """Get list of extension IDs to install."""
        # Try extensions.txt first (simple list)
        txt_file = self.export_path / "extensions.txt"
        if txt_file.exists():
            extensions = []
            with open(txt_file, "r", encoding="utf-8") as f:
                for line in f:
                    ext_id = line.strip()
                    if ext_id and not ext_id.startswith("#"):
                        extensions.append(ext_id)
            return extensions

        # Fall back to extensions.json
        json_file = self.export_path / "extensions.json"
        if json_file.exists():
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [ext["id"] for ext in data if ext.get("id")]

        return []


def install_extensions(
    extensions: list[str],
    skip_existing: bool = True,
    parallel: bool = False,
) -> tuple[int, int, int]:
    """Install extensions using Cursor CLI.

    Returns:
        Tuple of (installed, skipped, failed) counts
    """
    if not extensions:
        return 0, 0, 0

    # Get currently installed extensions
    installed_extensions = set()
    if skip_existing:
        try:
            result = subprocess.run(
                [CURSOR_CMD, "--list-extensions"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                installed_extensions = set(
                    ext.strip().lower()
                    for ext in result.stdout.strip().split("\n")
                    if ext.strip()
                )
        except Exception:
            pass

    installed = 0
    skipped = 0
    failed = 0

    print(f"\n  🧩 Installing {len(extensions)} extensions...")
    print(f"     (This may take a while)\n")

    for i, ext_id in enumerate(extensions, 1):
        # Check if already installed
        if skip_existing and ext_id.lower() in installed_extensions:
            print(f"    [{i}/{len(extensions)}] ⏭️  {ext_id} (already installed)")
            skipped += 1
            continue

        print(
            f"    [{i}/{len(extensions)}] 📦 Installing {ext_id}...",
            end=" ",
            flush=True,
        )

        try:
            result = subprocess.run(
                [CURSOR_CMD, "--install-extension", ext_id, "--force"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                print("✅")
                installed += 1
            else:
                print(f"❌ ({result.stderr.strip() or 'Unknown error'})")
                failed += 1

        except subprocess.TimeoutExpired:
            print("❌ (timeout)")
            failed += 1
        except Exception as e:
            print(f"❌ ({e})")
            failed += 1

    return installed, skipped, failed


def restore_profile(
    profile_name: str,
    export_path: Path,
    target_path: Path,
    is_default: bool,
    restore_extensions: bool = True,
    merge_settings: bool = False,
) -> dict:
    """Restore a single profile."""
    print(f"\n{'─' * 50}")
    print(f"📁 Restoring Profile: {profile_name}")
    print(f"   From: {export_path}")
    print(f"   To: {target_path}")
    print(f"{'─' * 50}")

    restorer = CursorDataRestore(export_path, target_path, is_default)

    # Restore settings
    print("\n  ⚙️  Restoring settings...")
    settings_ok = restorer.restore_settings(merge=merge_settings)

    # Restore keybindings
    print("\n  ⌨️  Restoring keybindings...")
    keybindings_ok = restorer.restore_keybindings()

    # Restore snippets
    print("\n  ✂️  Restoring snippets...")
    snippets_ok = restorer.restore_snippets()

    # Install extensions (only for default profile)
    installed = skipped = failed = 0
    if restore_extensions and is_default:
        extensions = restorer.get_extensions_to_install()
        if extensions:
            installed, skipped, failed = install_extensions(extensions)
        else:
            print("\n  ⚠️  No extensions found to install")

    return {
        "profile": profile_name,
        "settings": settings_ok,
        "keybindings": keybindings_ok,
        "snippets": snippets_ok,
        "extensions_installed": installed,
        "extensions_skipped": skipped,
        "extensions_failed": failed,
    }


def restore_global_data(export_dir: Path, paths: dict) -> bool:
    """Restore global Cursor data."""
    global_dir = export_dir / "_global"

    if not global_dir.exists():
        return False

    print(f"\n{'─' * 50}")
    print("🌐 Restoring global data...")
    print(f"{'─' * 50}")

    restored = False

    # Restore argv.json
    argv_source = global_dir / "argv.json"
    if argv_source.exists():
        argv_target = paths["data"] / "argv.json"
        try:
            paths["data"].mkdir(parents=True, exist_ok=True)
            shutil.copy2(argv_source, argv_target)
            print(f"  ✅ Restored argv.json")
            restored = True
        except Exception as e:
            print(f"  ❌ Error restoring argv.json: {e}")

    return restored


def interactive_menu() -> dict:
    """Show interactive menu for restore options."""
    print("\n📋 Restore Options:")
    print("─" * 30)

    options = {
        "restore_settings": True,
        "restore_keybindings": True,
        "restore_snippets": True,
        "restore_extensions": True,
        "merge_settings": False,
    }

    print("\nWhat would you like to restore?")
    print("  [1] Everything (default)")
    print("  [2] Settings only")
    print("  [3] Extensions only")
    print("  [4] Custom selection")
    print("  [q] Quit")

    choice = input("\nEnter choice [1]: ").strip() or "1"

    if choice.lower() == "q":
        sys.exit(0)
    elif choice == "2":
        options["restore_extensions"] = False
        options["restore_keybindings"] = False
        options["restore_snippets"] = False
    elif choice == "3":
        options["restore_settings"] = False
        options["restore_keybindings"] = False
        options["restore_snippets"] = False
    elif choice == "4":
        options["restore_settings"] = (
            input("  Restore settings? [Y/n]: ").strip().lower() != "n"
        )
        options["restore_keybindings"] = (
            input("  Restore keybindings? [Y/n]: ").strip().lower() != "n"
        )
        options["restore_snippets"] = (
            input("  Restore snippets? [Y/n]: ").strip().lower() != "n"
        )
        options["restore_extensions"] = (
            input("  Install extensions? [Y/n]: ").strip().lower() != "n"
        )

    if options["restore_settings"]:
        options["merge_settings"] = (
            input("\nMerge with existing settings? [y/N]: ").strip().lower() == "y"
        )

    return options


def main():
    """Main entry point."""
    print("=" * 50)
    print("🔄 Cursor IDE Data Restore")
    print("=" * 50)

    # Check if Cursor is installed
    print("\n🔍 Checking Cursor installation...")
    if not check_cursor_installed():
        print(f"⚠️  Warning: '{CURSOR_CMD}' command not found or not responding")
        print("   Extensions will not be installed automatically")
        print("   Settings and keybindings can still be restored\n")
        cursor_available = False
    else:
        print(f"✅ Cursor is available")
        cursor_available = True

    # Check export directory
    if not EXPORT_DIR.exists():
        print(f"\n❌ Export directory not found: {EXPORT_DIR}")
        print("   Run extract_cursor_data.py first to export your data")
        sys.exit(1)

    print(f"✅ Found export directory: {EXPORT_DIR}")

    # Get available profiles
    profiles = get_available_exports()

    if not profiles:
        print(f"\n❌ No profile exports found in {EXPORT_DIR}")
        sys.exit(1)

    print(f"\n✅ Found {len(profiles)} profile export(s):")
    for name, path, is_default in profiles:
        default_tag = " (default)" if is_default else ""
        print(f"   • {name}{default_tag}")

    # Get Cursor paths
    paths = get_cursor_paths()

    # Interactive options
    options = interactive_menu()

    # Confirm
    print("\n" + "=" * 50)
    print("⚠️  This will modify your Cursor configuration!")
    print("   Existing files will be backed up with .backup extension")
    print("=" * 50)

    confirm = input("\nProceed with restore? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        sys.exit(0)

    # Restore global data
    restore_global_data(EXPORT_DIR, paths)

    # Restore each profile
    results = []
    for profile_name, export_path, is_default in profiles:
        # Determine target path
        if is_default:
            target_path = paths["user"]
        else:
            target_path = paths["user"] / "profiles" / profile_name

        result = restore_profile(
            profile_name,
            export_path,
            target_path,
            is_default,
            restore_extensions=options["restore_extensions"] and cursor_available,
            merge_settings=options["merge_settings"],
        )
        results.append(result)

    # Print summary
    print(f"\n{'=' * 50}")
    print("📊 Restore Summary")
    print(f"{'=' * 50}")

    total_installed = 0
    total_skipped = 0
    total_failed = 0

    for result in results:
        print(f"\n  {result['profile']}:")
        print(f"    • Settings: {'✅' if result['settings'] else '⚠️'}")
        print(f"    • Keybindings: {'✅' if result['keybindings'] else '⚠️'}")
        print(f"    • Snippets: {'✅' if result['snippets'] else '⚠️'}")

        if result["extensions_installed"] or result["extensions_failed"]:
            print(
                f"    • Extensions: {result['extensions_installed']} installed, "
                f"{result['extensions_skipped']} skipped, "
                f"{result['extensions_failed']} failed"
            )

        total_installed += result["extensions_installed"]
        total_skipped += result["extensions_skipped"]
        total_failed += result["extensions_failed"]

    if total_installed or total_failed:
        print(f"\n  {'─' * 40}")
        print(
            f"  Extensions: {total_installed} installed, "
            f"{total_skipped} skipped, {total_failed} failed"
        )

    print(f"\n✨ Restore complete!")
    print(f"\n💡 Tip: Restart Cursor to apply all changes")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
