#!/usr/bin/env python3
"""
Konsole Terminal Data Extractor

Extracts Konsole configuration and profiles.
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

# Output directory from env or default
BACKUP_FOLDER_PATH = os.getenv("BACKUP_FOLDER_PATH", "")
EXPORT_DIR = Path(f"{BACKUP_FOLDER_PATH}/konsole-data/")


def export_konsole_config(output_dir: Path) -> bool:
    """Export Konsole main configuration."""
    print("\n⚙️  Exporting Konsole config...")

    konsole_config = KONSOLE_PATHS["config"]

    if not konsole_config.exists():
        print("  ⚠️  konsolerc not found")
        return False

    try:
        shutil.copy2(konsole_config, output_dir / "konsolerc")
        print("  ✅ Copied konsolerc")
        return True
    except Exception as e:
        print(f"  ❌ Error copying konsolerc: {e}")
        return False


def export_ssh_config(output_dir: Path) -> bool:
    """Export Konsole SSH configuration."""
    print("\n🔑 Exporting Konsole SSH config...")

    ssh_config = KONSOLE_PATHS["ssh_config"]

    if not ssh_config.exists():
        print("  ⚠️  konsolesshconfig not found (optional)")
        return False

    try:
        shutil.copy2(ssh_config, output_dir / "konsolesshconfig")
        print("  ✅ Copied konsolesshconfig")
        return True
    except Exception as e:
        print(f"  ❌ Error copying konsolesshconfig: {e}")
        return False


def export_profiles(output_dir: Path) -> bool:
    """Export Konsole profiles."""
    print("\n📁 Exporting Konsole profiles...")

    profiles_dir = KONSOLE_PATHS["profiles"]

    if not profiles_dir.exists():
        print("  ⚠️  Konsole profiles directory not found")
        return False

    profiles_output = output_dir / "profiles"

    try:
        # Copy entire profiles directory
        if profiles_output.exists():
            shutil.rmtree(profiles_output)
        shutil.copytree(profiles_dir, profiles_output)

        # Count profiles
        profile_count = len(list(profiles_output.glob("*.profile")))
        print(f"  ✅ Copied {profile_count} profile(s)")
        return True
    except Exception as e:
        print(f"  ❌ Error copying profiles: {e}")
        return False


def main():
    """Main entry point."""
    print("=" * 50)
    print("🖥️  Konsole Terminal Data Extractor")
    print("=" * 50)

    # Check if any Konsole data exists
    if not any(p.exists() for p in KONSOLE_PATHS.values()):
        print("\n❌ Konsole data not found!")
        print("\nExpected locations:")
        for name, path in KONSOLE_PATHS.items():
            print(f"  {name}: {path}")
        sys.exit(1)

    print("\n✅ Found Konsole data:")
    for name, path in KONSOLE_PATHS.items():
        status = "✓" if path.exists() else "✗"
        print(f"   [{status}] {name}: {path}")

    # Create output directory
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Export data
    config_ok = export_konsole_config(EXPORT_DIR)
    ssh_ok = export_ssh_config(EXPORT_DIR)
    profiles_ok = export_profiles(EXPORT_DIR)

    # Print summary
    print(f"\n{'=' * 50}")
    print("📊 Export Summary")
    print(f"{'=' * 50}")
    print(f"  • Config:   {'✅' if config_ok else '⚠️'}")
    print(f"  • SSH:      {'✅' if ssh_ok else '⚠️'}")
    print(f"  • Profiles: {'✅' if profiles_ok else '⚠️'}")
    print(f"\n✨ All exports saved to: {EXPORT_DIR.absolute()}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
