#!/usr/bin/env python3
"""
Fish Shell Data Restore

Restores fish shell history and configuration from backup.
"""

import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Fish shell paths
HOME = Path.home()
FISH_PATHS = {
    "history": HOME / ".local/share/fish/fish_history",
    "config": HOME / ".config/fish",
}

# Backup directory from env or default
BACKUP_FOLDER_PATH = os.getenv("BACKUP_FOLDER_PATH", "")
EXPORT_DIR = Path(f"{BACKUP_FOLDER_PATH}/fish-data/")


def check_backup_exists() -> bool:
    """Check if backup directory exists and has data."""
    if not EXPORT_DIR.exists():
        return False

    has_history = (EXPORT_DIR / "fish_history").exists()
    has_config = (EXPORT_DIR / "config").exists()

    return has_history or has_config


def restore_fish_history(backup: bool = True) -> bool:
    """Restore fish shell history."""
    print("\n🐟 Restoring fish history...")

    source = EXPORT_DIR / "fish_history"
    target = FISH_PATHS["history"]

    if not source.exists():
        print("  ⚠️  No fish_history found in backup")
        return False

    # Create parent directory if needed
    target.parent.mkdir(parents=True, exist_ok=True)

    # Backup existing history
    if backup and target.exists():
        backup_path = target.with_suffix(".bak")
        shutil.copy2(target, backup_path)
        print(f"  📦 Backed up existing history to: {backup_path.name}")

    try:
        shutil.copy2(source, target)
        print("  ✅ Restored fish_history")
        return True
    except Exception as e:
        print(f"  ❌ Error restoring fish_history: {e}")
        return False


def restore_fish_config(backup: bool = True) -> bool:
    """Restore fish shell configuration."""
    print("\n⚙️  Restoring fish config...")

    source = EXPORT_DIR / "config"
    target = FISH_PATHS["config"]

    if not source.exists():
        print("  ⚠️  No config directory found in backup")
        return False

    # Backup existing config
    if backup and target.exists():
        backup_path = target.with_suffix(".bak")
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.copytree(target, backup_path)
        print(f"  📦 Backed up existing config to: {backup_path.name}")

    try:
        # Remove existing config and restore from backup
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        print("  ✅ Restored fish config directory")
        return True
    except Exception as e:
        print(f"  ❌ Error restoring fish config: {e}")
        return False


def main():
    """Main entry point."""
    print("=" * 50)
    print("🐟 Fish Shell Data Restore")
    print("=" * 50)

    # Check for backup
    if not check_backup_exists():
        print(f"\n❌ No backup found in: {EXPORT_DIR}")
        print("\nRun the extract script first to create a backup.")
        sys.exit(1)

    # Show what will be restored
    print(f"\n✅ Found backup in: {EXPORT_DIR}")

    has_history = (EXPORT_DIR / "fish_history").exists()
    has_config = (EXPORT_DIR / "config").exists()

    print("\n📋 Available backups:")
    print(f"   [{'✓' if has_history else '✗'}] fish_history")
    print(f"   [{'✓' if has_config else '✗'}] config/")

    # Show target paths
    print("\n📍 Restore targets:")
    for name, path in FISH_PATHS.items():
        exists = "exists" if path.exists() else "will create"
        print(f"   • {name}: {path} ({exists})")

    # Confirm restore
    print("\n" + "=" * 50)
    print("⚠️  WARNING: This will overwrite existing fish data!")
    print("   Existing files will be backed up with .bak extension.")
    print("=" * 50)

    response = input("\nProceed with restore? [y/N]: ").strip().lower()
    if response != "y":
        print("\n❌ Restore cancelled.")
        sys.exit(0)

    # Perform restore
    history_ok = restore_fish_history(backup=True)
    config_ok = restore_fish_config(backup=True)

    # Print summary
    print(f"\n{'=' * 50}")
    print("📊 Restore Summary")
    print(f"{'=' * 50}")
    print(f"  • History: {'✅' if history_ok else '❌'}")
    print(f"  • Config:  {'✅' if config_ok else '❌'}")
    print(f"\n{'=' * 50}")
    print("✨ Restore complete!")
    print("\n💡 Restart your terminal or run 'source ~/.config/fish/config.fish'")
    print("=" * 50)


if __name__ == "__main__":
    main()
