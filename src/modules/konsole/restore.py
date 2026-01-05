#!/usr/bin/env python3
"""
Konsole Terminal Data Restore

Restores Konsole configuration and profiles from backup.
"""

import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Konsole paths
HOME = Path.home()
KONSOLE_PATHS = {
    "config": HOME / ".config/konsolerc",
    "ssh_config": HOME / ".config/konsolesshconfig",
    "profiles": HOME / ".local/share/konsole",
}

# Export directory from env or default
BACKUP_FOLDER_PATH = os.getenv("BACKUP_FOLDER_PATH", "")
EXPORT_DIR = Path(f"{BACKUP_FOLDER_PATH}/konsole-data/")


def restore_konsole_config(backup_dir: Path, backup: bool = True) -> bool:
    """Restore Konsole main configuration."""
    print("\n⚙️  Restoring Konsole config...")

    source = backup_dir / "konsolerc"
    target = KONSOLE_PATHS["config"]

    if not source.exists():
        print("  ⚠️  No konsolerc found in backup")
        return False

    try:
        # Backup existing if present
        if target.exists() and backup:
            backup_file = target.with_suffix(".backup")
            shutil.copy2(target, backup_file)
            print(f"  📦 Backed up existing to {backup_file.name}")

        # Create parent directory if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        # Copy from backup
        shutil.copy2(source, target)
        print("  ✅ Restored konsolerc")
        return True
    except Exception as e:
        print(f"  ❌ Error restoring konsolerc: {e}")
        return False


def restore_ssh_config(backup_dir: Path, backup: bool = True) -> bool:
    """Restore Konsole SSH configuration."""
    print("\n🔑 Restoring Konsole SSH config...")

    source = backup_dir / "konsolesshconfig"
    target = KONSOLE_PATHS["ssh_config"]

    if not source.exists():
        print("  ⚠️  No konsolesshconfig found in backup")
        return False

    try:
        # Backup existing if present
        if target.exists() and backup:
            backup_file = target.with_suffix(".backup")
            shutil.copy2(target, backup_file)
            print(f"  📦 Backed up existing to {backup_file.name}")

        # Create parent directory if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        # Copy from backup
        shutil.copy2(source, target)
        print("  ✅ Restored konsolesshconfig")
        return True
    except Exception as e:
        print(f"  ❌ Error restoring konsolesshconfig: {e}")
        return False


def restore_profiles(backup_dir: Path, backup: bool = True) -> bool:
    """Restore Konsole profiles."""
    print("\n📁 Restoring Konsole profiles...")

    source_dir = backup_dir / "profiles"
    target_dir = KONSOLE_PATHS["profiles"]

    if not source_dir.exists():
        print("  ⚠️  No profiles directory found in backup")
        return False

    try:
        # Create target directory if needed
        target_dir.mkdir(parents=True, exist_ok=True)

        restored = 0
        for profile_file in source_dir.glob("*.profile"):
            target_file = target_dir / profile_file.name

            # Backup existing if present
            if target_file.exists() and backup:
                backup_file = target_file.with_suffix(".profile.backup")
                shutil.copy2(target_file, backup_file)

            shutil.copy2(profile_file, target_file)
            restored += 1

        print(f"  ✅ Restored {restored} profile(s)")
        return True
    except Exception as e:
        print(f"  ❌ Error restoring profiles: {e}")
        return False


def main():
    """Main entry point."""
    print("=" * 50)
    print("🖥️  Konsole Terminal Data Restore")
    print("=" * 50)

    # Check backup directory
    if not EXPORT_DIR.exists():
        print(f"\n❌ Backup directory not found: {EXPORT_DIR}")
        print("   Run extract.py first to backup your data")
        sys.exit(1)

    print(f"\n✅ Found backup directory: {EXPORT_DIR}")

    # Show what's available
    print("\n📋 Available backups:")
    print(f"   [{'✓' if (EXPORT_DIR / 'konsolerc').exists() else '✗'}] konsolerc")
    print(
        f"   [{'✓' if (EXPORT_DIR / 'konsolesshconfig').exists() else '✗'}] konsolesshconfig"
    )
    print(f"   [{'✓' if (EXPORT_DIR / 'profiles').exists() else '✗'}] profiles/")

    # Confirm restore
    print("\n" + "=" * 50)
    print("⚠️  This will overwrite your current Konsole configuration!")
    print("   Existing files will be backed up with .backup extension")
    print("=" * 50)

    confirm = input("\nProceed with restore? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        sys.exit(0)

    # Restore data
    config_ok = restore_konsole_config(EXPORT_DIR)
    ssh_ok = restore_ssh_config(EXPORT_DIR)
    profiles_ok = restore_profiles(EXPORT_DIR)

    # Print summary
    print(f"\n{'=' * 50}")
    print("📊 Restore Summary")
    print(f"{'=' * 50}")
    print(f"  • Config:   {'✅' if config_ok else '⚠️'}")
    print(f"  • SSH:      {'✅' if ssh_ok else '⚠️'}")
    print(f"  • Profiles: {'✅' if profiles_ok else '⚠️'}")
    print(f"\n✨ Restore complete!")
    print(f"\n💡 Tip: Restart Konsole to apply changes")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
