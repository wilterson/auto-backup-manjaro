#!/usr/bin/env python3
"""
Fish Shell Data Extractor

Extracts fish shell history and configuration files.
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

# Output directory from env or default
BACKUP_FOLDER_PATH = os.getenv("BACKUP_FOLDER_PATH", "")
EXPORT_DIR = Path(f"{BACKUP_FOLDER_PATH}/fish-data/")


def export_fish_history(output_dir: Path) -> bool:
    """Export fish shell history."""
    print("\n🐟 Exporting fish history...")

    fish_history = FISH_PATHS["history"]

    if not fish_history.exists():
        print("  ⚠️  Fish history not found")
        return False

    try:
        shutil.copy2(fish_history, output_dir / "fish_history")
        print(f"  ✅ Copied fish_history")
        return True
    except Exception as e:
        print(f"  ❌ Error copying fish_history: {e}")
        return False


def export_fish_config(output_dir: Path) -> bool:
    """Export fish shell configuration files."""
    print("\n⚙️  Exporting fish config...")

    fish_config = FISH_PATHS["config"]

    if not fish_config.exists():
        print("  ⚠️  Fish config directory not found")
        return False

    config_output = output_dir / "config"

    try:
        # Copy entire fish config directory
        if config_output.exists():
            shutil.rmtree(config_output)
        shutil.copytree(fish_config, config_output)
        print(f"  ✅ Copied fish config directory")
        return True
    except Exception as e:
        print(f"  ❌ Error copying fish config: {e}")
        return False


def main():
    """Main entry point."""
    print("=" * 50)
    print("🐟 Fish Shell Data Extractor")
    print("=" * 50)

    # Check if fish data exists
    if not any(p.exists() for p in FISH_PATHS.values()):
        print("\n❌ Fish shell data not found!")
        print("\nExpected locations:")
        for name, path in FISH_PATHS.items():
            print(f"  {name}: {path}")
        sys.exit(1)

    print(f"\n✅ Found fish shell data:")
    for name, path in FISH_PATHS.items():
        status = "✓" if path.exists() else "✗"
        print(f"   [{status}] {name}: {path}")

    # Create output directory
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Export data
    history_ok = export_fish_history(EXPORT_DIR)
    config_ok = export_fish_config(EXPORT_DIR)

    # Print summary
    print(f"\n{'=' * 50}")
    print("📊 Export Summary")
    print(f"{'=' * 50}")
    print(f"  • History: {'✅' if history_ok else '❌'}")
    print(f"  • Config:  {'✅' if config_ok else '❌'}")
    print(f"\n✨ All exports saved to: {EXPORT_DIR.absolute()}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
