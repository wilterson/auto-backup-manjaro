import os
import sys

from dotenv import load_dotenv

from modules.brave import extract as extract_brave
from modules.cursor import extract as extract_cursor
from modules.fish import extract as extract_fish
from modules.konsole import extract as extract_konsole
import backup_to_drive

load_dotenv()

BACKUP_FOLDER_PATH = os.getenv("BACKUP_FOLDER_PATH", "")


def main():
    # Check if backup folder path is set
    if not BACKUP_FOLDER_PATH:
        print("❌ Error: BACKUP_FOLDER_PATH not set in .env file")
        print("Please create a .env file with the path to backup")
        sys.exit(1)

    print("=" * 50)
    print("🔄 Auto Backup Tools")
    print(f"✅ Backup folder path: {BACKUP_FOLDER_PATH}")
    print("=" * 50 + "\n")

    # Extract Fish data
    extract_fish.main()

    # Extract Brave data
    extract_brave.main()

    # Extract Cursor data
    extract_cursor.main()

    # Extract Konsole data
    extract_konsole.main()

    print("Uploading data to Google Drive...")
    backup_to_drive.main()


if __name__ == "__main__":
    main()
