#!/usr/bin/env python3
"""
Cursor IDE Data Extractor

Extracts settings, keybindings, snippets, and extensions from Cursor IDE.
Supports multiple profiles.
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


def strip_jsonc_comments(text: str) -> str:
    """Remove comments from JSONC (JSON with Comments) content."""
    # Remove single-line comments (// ...)
    # Be careful not to remove // inside strings
    result = []
    in_string = False
    i = 0
    while i < len(text):
        char = text[i]

        # Handle string boundaries
        if char == '"' and (i == 0 or text[i - 1] != "\\"):
            in_string = not in_string
            result.append(char)
            i += 1
        # Handle single-line comments outside strings
        elif not in_string and char == "/" and i + 1 < len(text) and text[i + 1] == "/":
            # Skip until end of line
            while i < len(text) and text[i] != "\n":
                i += 1
        # Handle block comments outside strings
        elif not in_string and char == "/" and i + 1 < len(text) and text[i + 1] == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2  # Skip */
        else:
            result.append(char)
            i += 1

    content = "".join(result)

    # Remove trailing commas before } or ]
    content = re.sub(r",(\s*[}\]])", r"\1", content)

    return content


load_dotenv()

# Cursor IDE paths in Linux
HOME = Path.home()
CURSOR_PATHS = {
    "config": HOME / ".config/Cursor",
    "data": HOME / ".cursor",
}

# Output directory from env or default
BACKUP_FOLDER_PATH = os.getenv("BACKUP_FOLDER_PATH", "")
EXPORT_DIR = Path(f"{BACKUP_FOLDER_PATH}/cursor-data/")


def get_cursor_paths() -> dict | None:
    """Get Cursor IDE paths for the current system."""
    config_path = CURSOR_PATHS["config"]
    data_path = CURSOR_PATHS["data"]

    if not config_path.exists() and not data_path.exists():
        return None

    return {
        "config": config_path,
        "data": data_path,
        "user": config_path / "User",
        "extensions": data_path / "extensions",
    }


def get_all_cursor_profiles(paths: dict) -> list[tuple[str, Path, bool]]:
    """Find all Cursor IDE profiles.

    Returns:
        List of tuples containing (profile_name, profile_path, is_default)
    """
    profiles = []
    user_path = paths["user"]

    if not user_path.exists():
        return profiles

    # Add default profile
    if (user_path / "settings.json").exists() or (
        user_path / "keybindings.json"
    ).exists():
        profiles.append(("Default", user_path, True))

    # Find additional profiles
    profiles_dir = user_path / "profiles"
    if profiles_dir.exists():
        for profile_dir in profiles_dir.iterdir():
            if profile_dir.is_dir():
                # Try to get profile name from settings or use directory name
                profile_name = profile_dir.name
                settings_file = profile_dir / "settings.json"

                if settings_file.exists():
                    try:
                        with open(settings_file, "r", encoding="utf-8") as f:
                            settings = json.load(f)
                            # Check for profile name in workbench settings
                            theme = settings.get("workbench.colorTheme", "")
                            if theme:
                                profile_name = f"{profile_dir.name} ({theme})"
                    except (json.JSONDecodeError, KeyError):
                        pass

                profiles.append((profile_name, profile_dir, False))

    return profiles


class CursorDataExtractor:
    """Extracts settings, keybindings, snippets, and extensions from Cursor IDE."""

    def __init__(self, profile_path: Path, output_dir: Path, is_default: bool = False):
        self.profile_path = profile_path
        self.output_dir = output_dir
        self.is_default = is_default

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_settings(self) -> dict:
        """Extract settings.json from the profile (preserves comments)."""
        settings_file = self.profile_path / "settings.json"

        if not settings_file.exists():
            print("    ⚠️  settings.json not found")
            return {}

        try:
            # Copy original file as-is (preserves comments)
            shutil.copy2(settings_file, self.output_dir / "settings.json")

            # Parse for counting only
            with open(settings_file, "r", encoding="utf-8") as f:
                content = f.read()
            clean_content = strip_jsonc_comments(content)
            settings = json.loads(clean_content) if clean_content.strip() else {}
            print(f"    ✅ Copied settings.json ({len(settings)} settings)")
            return settings
        except json.JSONDecodeError as e:
            # Still copy the file even if parsing fails
            shutil.copy2(settings_file, self.output_dir / "settings.json")
            print(f"    ⚠️  Copied settings.json (could not parse for count: {e})")
            return {}

    def extract_keybindings(self) -> list:
        """Extract keybindings.json from the profile (preserves comments)."""
        keybindings_file = self.profile_path / "keybindings.json"

        if not keybindings_file.exists():
            print("    ⚠️  keybindings.json not found")
            return []

        try:
            # Copy original file as-is (preserves comments)
            shutil.copy2(keybindings_file, self.output_dir / "keybindings.json")

            # Parse for counting only
            with open(keybindings_file, "r", encoding="utf-8") as f:
                content = f.read()
            clean_content = strip_jsonc_comments(content)
            keybindings = json.loads(clean_content) if clean_content.strip() else []

            print(f"    ✅ Copied keybindings.json ({len(keybindings)} keybindings)")
            return keybindings
        except json.JSONDecodeError as e:
            # Still copy the file even if parsing fails
            shutil.copy2(keybindings_file, self.output_dir / "keybindings.json")
            print(f"    ⚠️  Copied keybindings.json (could not parse for count: {e})")
            return []

    def extract_snippets(self) -> dict[str, dict]:
        """Extract snippets from the profile (preserves comments)."""
        snippets_dir = self.profile_path / "snippets"
        snippets = {}

        if not snippets_dir.exists():
            print("    ⚠️  snippets directory not found")
            return snippets

        # Copy entire snippets directory as-is (preserves comments)
        output_snippets_dir = self.output_dir / "snippets"
        if output_snippets_dir.exists():
            shutil.rmtree(output_snippets_dir)
        shutil.copytree(snippets_dir, output_snippets_dir)

        # Parse for counting only
        for snippet_file in snippets_dir.glob("*.json"):
            try:
                with open(snippet_file, "r", encoding="utf-8") as f:
                    content = f.read()
                clean_content = strip_jsonc_comments(content)
                snippet_data = (
                    json.loads(clean_content) if clean_content.strip() else {}
                )
                if snippet_data:
                    snippets[snippet_file.stem] = snippet_data
            except json.JSONDecodeError:
                continue

        total_snippets = sum(len(s) for s in snippets.values())
        print(
            f"    ✅ Copied snippets/ ({total_snippets} snippets from {len(snippets)} files)"
        )
        return snippets

    def extract_extensions(self, extensions_path: Path) -> list[dict]:
        """Extract installed extensions list."""
        extensions_file = extensions_path / "extensions.json"

        if not extensions_file.exists():
            print("    ⚠️  extensions.json not found")
            return []

        try:
            with open(extensions_file, "r", encoding="utf-8") as f:
                extensions_data = json.load(f)

            extensions = []
            for ext in extensions_data:
                identifier = ext.get("identifier", {})
                metadata = ext.get("metadata", {})

                extensions.append(
                    {
                        "id": identifier.get("id", ""),
                        "version": ext.get("version", ""),
                        "publisher": metadata.get("publisherDisplayName", ""),
                        "installed_timestamp": metadata.get("installedTimestamp"),
                        "source": metadata.get("source", ""),
                    }
                )

            # Sort by extension ID
            extensions.sort(key=lambda x: x["id"].lower())
            print(f"    ✅ Extracted {len(extensions)} extensions")
            return extensions
        except json.JSONDecodeError as e:
            print(f"    ❌ Error parsing extensions.json: {e}")
            return []

    def extract_profile_extensions(self) -> list[dict]:
        """Extract profile-specific extensions."""
        extensions_file = self.profile_path / "extensions.json"

        if not extensions_file.exists():
            return []

        try:
            with open(extensions_file, "r", encoding="utf-8") as f:
                extensions_data = json.load(f)

            extensions = []
            for ext in extensions_data:
                identifier = ext.get("identifier", {})
                metadata = ext.get("metadata", {})

                extensions.append(
                    {
                        "id": identifier.get("id", ""),
                        "version": ext.get("version", ""),
                        "publisher": metadata.get("publisherDisplayName", ""),
                    }
                )

            extensions.sort(key=lambda x: x["id"].lower())
            if extensions:
                print(f"    ✅ Extracted {len(extensions)} profile-specific extensions")
            return extensions
        except json.JSONDecodeError:
            return []

    def export_settings(self, settings: dict, filename: str = "settings.json"):
        """Export settings to JSON file."""
        if not settings:
            return

        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        print(f"    📄 Settings exported to: {output_path}")

    def export_keybindings(self, keybindings: list, filename: str = "keybindings.json"):
        """Export keybindings to JSON file."""
        if not keybindings:
            return

        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(keybindings, f, indent=2, ensure_ascii=False)
        print(f"    📄 Keybindings exported to: {output_path}")

    def export_snippets(self, snippets: dict[str, dict]):
        """Export snippets to individual JSON files."""
        if not snippets:
            return

        snippets_dir = self.output_dir / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)

        for name, data in snippets.items():
            output_path = snippets_dir / f"{name}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"    📄 Snippets exported to: {snippets_dir}")

    def export_extensions(
        self, extensions: list[dict], filename: str = "extensions.json"
    ):
        """Export extensions list to JSON file."""
        if not extensions:
            return

        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(extensions, f, indent=2, ensure_ascii=False)
        print(f"    📄 Extensions exported to: {output_path}")

    def export_extensions_list(
        self, extensions: list[dict], filename: str = "extensions.txt"
    ):
        """Export extensions as a simple list (for easy reinstall)."""
        if not extensions:
            return

        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Cursor IDE Extensions\n")
            f.write(f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total: {len(extensions)} extensions\n")
            f.write("#\n")
            f.write("# To install, run:\n")
            f.write("#   cursor --install-extension <extension-id>\n")
            f.write("#\n\n")

            for ext in extensions:
                f.write(f"{ext['id']}\n")

        print(f"    📄 Extensions list exported to: {output_path}")


def export_profile(
    profile_name: str,
    profile_path: Path,
    is_default: bool,
    base_output_dir: Path,
    extensions_path: Path,
) -> dict:
    """Export data from a single profile."""
    # Create a safe folder name
    safe_name = "Default" if is_default else profile_path.name
    profile_output_dir = base_output_dir / safe_name

    print(f"\n{'─' * 50}")
    print(f"📁 Profile: {profile_name}")
    print(f"   Path: {profile_path}")
    print(f"   Output: {profile_output_dir}")
    print(f"{'─' * 50}")

    extractor = CursorDataExtractor(profile_path, profile_output_dir, is_default)

    # Extract settings (copies file as-is, preserving comments)
    print("\n  ⚙️  Extracting settings...")
    settings = extractor.extract_settings()

    # Extract keybindings (copies file as-is, preserving comments)
    print("\n  ⌨️  Extracting keybindings...")
    keybindings = extractor.extract_keybindings()

    # Extract snippets (copies directory as-is, preserving comments)
    print("\n  ✂️  Extracting snippets...")
    snippets = extractor.extract_snippets()

    # Extract extensions (only for default profile, as extensions are shared)
    extensions = []
    if is_default and extensions_path.exists():
        print("\n  🧩 Extracting extensions...")
        extensions = extractor.extract_extensions(extensions_path)
        if extensions:
            extractor.export_extensions(extensions)
            extractor.export_extensions_list(extensions)
    else:
        # Check for profile-specific extensions
        print("\n  🧩 Checking profile extensions...")
        profile_extensions = extractor.extract_profile_extensions()
        if profile_extensions:
            extractor.export_extensions(profile_extensions, "profile_extensions.json")

    return {
        "profile": profile_name,
        "settings_count": len(settings),
        "keybindings_count": len(keybindings),
        "snippets_count": sum(len(s) for s in snippets.values()),
        "extensions_count": len(extensions),
    }


def export_global_data(paths: dict, base_output_dir: Path):
    """Export global Cursor data (not profile-specific)."""
    print(f"\n{'─' * 50}")
    print("🌐 Exporting global data...")
    print(f"{'─' * 50}")

    global_dir = base_output_dir / "_global"
    global_dir.mkdir(parents=True, exist_ok=True)

    # Export argv.json (Cursor startup arguments)
    argv_file = paths["data"] / "argv.json"
    if argv_file.exists():
        try:
            shutil.copy2(argv_file, global_dir / "argv.json")
            print(f"  📄 Copied argv.json")
        except Exception as e:
            print(f"  ❌ Error copying argv.json: {e}")

    # Export project list if available
    projects_file = paths["data"] / "unified_repo_list.json"
    if projects_file.exists():
        try:
            with open(projects_file, "r", encoding="utf-8") as f:
                projects = json.load(f)
            with open(global_dir / "projects.json", "w", encoding="utf-8") as f:
                json.dump(projects, f, indent=2, ensure_ascii=False)
            print(f"  📄 Exported projects list")
        except Exception as e:
            print(f"  ❌ Error exporting projects: {e}")

    # Export storage.json (global storage settings)
    storage_file = paths["user"] / "globalStorage" / "storage.json"
    if storage_file.exists():
        try:
            shutil.copy2(storage_file, global_dir / "globalStorage.json")
            print(f"  📄 Copied globalStorage.json")
        except Exception as e:
            print(f"  ❌ Error copying globalStorage.json: {e}")


def main():
    """Main entry point."""
    print("=" * 50)
    print("🖥️  Cursor IDE Data Extractor")
    print("=" * 50)

    # Get Cursor paths
    paths = get_cursor_paths()

    if not paths:
        print("\n❌ Cursor IDE data not found!")
        print("\nExpected locations:")
        for name, path in CURSOR_PATHS.items():
            print(f"  {name}: {path}")
        sys.exit(1)

    print(f"\n✅ Found Cursor IDE data:")
    print(f"   Config: {paths['config']}")
    print(f"   Data: {paths['data']}")

    # Find all profiles
    profiles = get_all_cursor_profiles(paths)

    if not profiles:
        print("\n❌ No Cursor IDE profiles found!")
        sys.exit(1)

    print(f"\n✅ Found {len(profiles)} profile(s):")
    for name, path, is_default in profiles:
        default_tag = " (default)" if is_default else ""
        print(f"   • {name}{default_tag}")

    # Export global data
    export_global_data(paths, EXPORT_DIR)

    # Export each profile
    results = []
    for profile_name, profile_path, is_default in profiles:
        result = export_profile(
            profile_name,
            profile_path,
            is_default,
            EXPORT_DIR,
            paths["extensions"],
        )
        results.append(result)

    # Print summary
    print(f"\n{'=' * 50}")
    print("📊 Export Summary")
    print(f"{'=' * 50}")

    total_settings = 0
    total_keybindings = 0
    total_snippets = 0
    total_extensions = 0

    for result in results:
        print(f"\n  {result['profile']}:")
        print(f"    • Settings: {result['settings_count']}")
        print(f"    • Keybindings: {result['keybindings_count']}")
        print(f"    • Snippets: {result['snippets_count']}")
        if result["extensions_count"]:
            print(f"    • Extensions: {result['extensions_count']}")

        total_settings += result["settings_count"]
        total_keybindings += result["keybindings_count"]
        total_snippets += result["snippets_count"]
        total_extensions += result["extensions_count"]

    print(f"\n  {'─' * 40}")
    print(f"  Total: {total_settings} settings, {total_keybindings} keybindings,")
    print(f"         {total_snippets} snippets, {total_extensions} extensions")
    print(f"\n✨ All exports saved to: {EXPORT_DIR.absolute()}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
