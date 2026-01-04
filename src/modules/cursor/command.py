#!/usr/bin/env python3
"""
Cursor Command Trigger

Triggers Cursor IDE commands using xdotool.
Useful for automating actions that can't be done via CLI.
"""

import argparse
import shutil
import subprocess
import sys
import time

# Sync commands
COMMANDS = {
    "sync-now": "Sync: Download Settings",
    "sync-upload": "Sync: Update/Upload Settings",
}


def check_xdotool() -> bool:
    """Check if xdotool is installed."""
    return shutil.which("xdotool") is not None


def find_cursor_window() -> str | None:
    """Find the Cursor window ID."""
    try:
        result = subprocess.run(
            ["xdotool", "search", "--name", "Cursor"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            windows = result.stdout.strip().split("\n")
            return windows[0]

        result = subprocess.run(
            ["xdotool", "search", "--class", "Cursor"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            windows = result.stdout.strip().split("\n")
            return windows[0]

        return None
    except Exception:
        return None


def focus_window(window_id: str) -> bool:
    """Focus a window by ID."""
    try:
        result = subprocess.run(
            ["xdotool", "windowactivate", "--sync", window_id],
            capture_output=True,
            timeout=5,
        )
        time.sleep(0.3)
        return result.returncode == 0
    except Exception:
        return False


def send_keys(keys: str, delay: float = 0.1) -> bool:
    """Send keystrokes using xdotool."""
    try:
        time.sleep(delay)
        result = subprocess.run(
            ["xdotool", "key", "--clearmodifiers", keys],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def type_text(text: str, delay: float = 0.05) -> bool:
    """Type text using xdotool."""
    try:
        time.sleep(delay)
        result = subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "20", text],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def execute_cursor_command(command_text: str, wait_after: float = 0.5) -> bool:
    """Execute a command in Cursor via the command palette."""
    print(f"🎯 Executing: {command_text}")

    # Find Cursor window
    print("  🔍 Finding Cursor window...", end=" ", flush=True)
    window_id = find_cursor_window()

    if not window_id:
        print("❌")
        print("  ⚠️  Cursor window not found. Is Cursor running?")
        return False
    print("✅")

    # Focus Cursor window
    print("  🪟 Focusing window...", end=" ", flush=True)
    if not focus_window(window_id):
        print("❌")
        print("  ⚠️  Could not focus Cursor window")
        return False
    print("✅")

    # Open command palette (Ctrl+Shift+P)
    print("  ⌨️  Opening command palette...", end=" ", flush=True)
    if not send_keys("ctrl+shift+p", delay=0.2):
        print("❌")
        return False
    print("✅")

    # Wait for palette to open
    time.sleep(0.4)

    # Type the command
    print("  📝 Typing command...", end=" ", flush=True)
    if not type_text(command_text):
        print("❌")
        return False
    print("✅")

    # Wait a moment for autocomplete
    time.sleep(0.3)

    # Press Enter to execute
    print("  ⏎  Executing...", end=" ", flush=True)
    if not send_keys("Return"):
        print("❌")
        return False
    print("✅")

    # Wait for command to complete
    time.sleep(wait_after)

    return True


def list_commands():
    """List available predefined commands."""
    print("\n📋 Available Commands:")
    print("─" * 50)

    max_key_len = max(len(k) for k in COMMANDS.keys())

    for key, value in sorted(COMMANDS.items()):
        print(f"  {key:<{max_key_len}}  →  {value}")

    print("\n💡 You can also use any custom command text with --custom")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Trigger Cursor IDE commands using xdotool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s sync-now              # Sync settings (download)
  %(prog)s sync-upload           # Upload local settings to cloud
  %(prog)s --custom "My Command" # Run a custom command
  %(prog)s --list                # List all predefined commands
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=list(COMMANDS.keys()),
        help="Predefined command to execute",
    )

    parser.add_argument(
        "--custom",
        "-c",
        type=str,
        help="Custom command text to execute",
    )

    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all available predefined commands",
    )

    parser.add_argument(
        "--wait",
        "-w",
        type=float,
        default=0.5,
        help="Seconds to wait after command execution (default: 0.5)",
    )

    args = parser.parse_args()

    # List commands
    if args.list:
        list_commands()
        return 0

    # Check for command
    if not args.command and not args.custom:
        parser.print_help()
        print("\n❌ Error: Please specify a command or use --custom")
        return 1

    # Header
    print("=" * 50)
    print("🖱️  Cursor Command Trigger")
    print("=" * 50 + "\n")

    # Check xdotool
    print("🔍 Checking requirements...")

    if not check_xdotool():
        print("❌ xdotool is not installed!")
        print("\nInstall it with:")
        print("  sudo pacman -S xdotool")
        return 1

    print("  ✅ xdotool is available")

    # Get command text
    if args.custom:
        command_text = args.custom
    else:
        command_text = COMMANDS[args.command]

    print()

    # Execute command
    success = execute_cursor_command(command_text, wait_after=args.wait)

    print()
    if success:
        print("✨ Command executed successfully!")
        return 0
    else:
        print("❌ Command execution failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
