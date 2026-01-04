import io
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from modules.brave import restore as restore_brave
from modules.cursor import restore as restore_cursor
from modules.fish import restore as restore_fish
from modules.github import setup_ssh

load_dotenv()

# Google Drive API scopes
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Configuration from environment
BACKUP_FOLDER_PATH = os.getenv("BACKUP_FOLDER_PATH", "")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google-creds.json")


class GoogleDriveRestore:
    """Handles downloading backups from Google Drive."""

    def __init__(self):
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with Google Drive API using Service Account."""
        if not os.path.exists(CREDENTIALS_FILE):
            print(f"❌ Error: {CREDENTIALS_FILE} not found!")
            sys.exit(1)

        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )

        self.service = build("drive", "v3", credentials=creds)
        print("✅ Connected to Google Drive (Service Account)")

    def find_latest_backup(self, parent_folder_id: str = None) -> dict | None:
        """Find the most recent backup folder on Google Drive."""
        query = "mimeType='application/vnd.google-apps.folder' and trashed=false and name contains 'backup_'"
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"

        results = (
            self.service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name, createdTime)",
                orderBy="createdTime desc",
                pageSize=1,
            )
            .execute()
        )

        files = results.get("files", [])
        return files[0] if files else None

    def list_files_in_folder(self, folder_id: str) -> list:
        """List all files and folders in a Google Drive folder."""
        results = (
            self.service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces="drive",
                fields="files(id, name, mimeType)",
            )
            .execute()
        )
        return results.get("files", [])

    def download_file(self, file_id: str, file_name: str, local_path: Path) -> bool:
        """Download a single file from Google Drive."""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_path = local_path / file_name

            with io.FileIO(str(file_path), "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()

            print(f"  ✅ Downloaded: {file_name}")
            return True
        except Exception as e:
            print(f"  ❌ Error downloading {file_name}: {e}")
            return False

    def download_folder(self, folder_id: str, local_path: Path):
        """Recursively download a folder from Google Drive."""
        local_path.mkdir(parents=True, exist_ok=True)

        items = self.list_files_in_folder(folder_id)

        for item in items:
            if item["mimeType"] == "application/vnd.google-apps.folder":
                # Recursively download subfolder
                subfolder_path = local_path / item["name"]
                self.download_folder(item["id"], subfolder_path)
            else:
                self.download_file(item["id"], item["name"], local_path)

    def restore_from_drive(self, local_backup_path: str) -> bool:
        """Download the latest backup from Google Drive."""
        print("\n🔍 Searching for backups on Google Drive...")

        latest_backup = self.find_latest_backup(GOOGLE_DRIVE_FOLDER_ID or None)

        if not latest_backup:
            print("❌ No backup found on Google Drive!")
            return False

        print(f"✅ Found backup: {latest_backup['name']}")
        print(f"   Created: {latest_backup['createdTime']}")

        response = input("\nDownload this backup? [y/N]: ").strip().lower()
        if response != "y":
            print("❌ Download cancelled.")
            return False

        print(f"\n📥 Downloading backup to: {local_backup_path}")

        local_path = Path(local_backup_path)
        self.download_folder(latest_backup["id"], local_path)

        print("\n✅ Backup downloaded successfully!")
        return True


def main():
    print("=" * 50)
    print("🔄 Auto Restore Tool")
    print("=" * 50)

    # Step 1: Install packages
    print("\n📦 Installing packages...")
    subprocess.run(["sh", "src/packages/install_packages.sh"], check=True)

    # Step 2: Check for backup on Google Drive
    print("\n" + "=" * 50)
    print("☁️  Checking Google Drive for backups...")
    print("=" * 50)

    if not BACKUP_FOLDER_PATH:
        print("❌ Error: BACKUP_FOLDER_PATH not set in .env file")
        sys.exit(1)

    drive_restore = GoogleDriveRestore()
    backup_available = drive_restore.restore_from_drive(BACKUP_FOLDER_PATH)

    if not backup_available:
        print("\n⚠️  No backup downloaded. Skipping restore.")
        return

    # Step 3: Restore data from downloaded backup
    print("\n" + "=" * 50)
    print("📂 Restoring data from backup...")
    print("=" * 50)

    # Restore Fish data
    restore_fish.main()

    # Restore Brave data
    restore_brave.main()

    # Restore Cursor data
    restore_cursor.main()

    # Step 4: Setup GitHub SSH
    print("\n" + "=" * 50)
    print("🔐 Setting up GitHub SSH...")
    print("=" * 50)
    setup_ssh.main()

    print("\n" + "=" * 50)
    print("✨ Restore complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
