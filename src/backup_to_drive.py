#!/usr/bin/env python3
"""
Auto Backup to Google Drive

This script uploads files from a specified local folder to Google Drive.
It supports incremental backups by checking if files already exist.
"""

import os
import sys
import mimetypes
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Google Drive API scopes
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Configuration from environment
BACKUP_FOLDER_PATH = os.getenv("BACKUP_FOLDER_PATH", "")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google-creds.json")
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "google-token.json")


class GoogleDriveBackup:
    """Handles file uploads to Google Drive."""

    def __init__(self):
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with Google Drive API using Service Account."""
        if not os.path.exists(CREDENTIALS_FILE):
            print(f"❌ Error: {CREDENTIALS_FILE} not found!")
            print("\nTo set up Google Drive API:")
            print("1. Go to https://console.cloud.google.com/")
            print("2. Create a new project or select existing one")
            print("3. Enable the Google Drive API")
            print("4. Create a Service Account and download JSON key")
            print("5. Share your Drive folder with the service account email")
            sys.exit(1)

        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )

        self.service = build("drive", "v3", credentials=creds)
        print("✅ Connected to Google Drive (Service Account)")

    def get_or_create_folder(self, folder_name: str, parent_id: str = None) -> str:
        """Get existing folder ID or create a new folder in Google Drive."""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = (
            self.service.files()
            .list(q=query, spaces="drive", fields="files(id, name)")
            .execute()
        )

        files = results.get("files", [])

        if files:
            return files[0]["id"]

        # Create folder
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            file_metadata["parents"] = [parent_id]

        folder = self.service.files().create(body=file_metadata, fields="id").execute()

        print(f"📁 Created folder: {folder_name}")
        return folder.get("id")

    def file_exists(self, filename: str, parent_id: str = None) -> dict | None:
        """Check if a file already exists in the specified folder."""
        query = f"name='{filename}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = (
            self.service.files()
            .list(q=query, spaces="drive", fields="files(id, name, modifiedTime, size)")
            .execute()
        )

        files = results.get("files", [])
        return files[0] if files else None

    def upload_file(
        self, file_path: str, parent_folder_id: str = None, update_existing: bool = True
    ) -> bool:
        """Upload a single file to Google Drive."""
        file_path = Path(file_path)

        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return False

        filename = file_path.name
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"

        # Check if file already exists
        existing_file = self.file_exists(filename, parent_folder_id)

        media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)

        try:
            if existing_file and update_existing:
                # Update existing file
                file = (
                    self.service.files()
                    .update(fileId=existing_file["id"], media_body=media)
                    .execute()
                )
                print(f"🔄 Updated: {filename}")
            else:
                # Create new file
                file_metadata = {"name": filename}
                if parent_folder_id:
                    file_metadata["parents"] = [parent_folder_id]

                file = (
                    self.service.files()
                    .create(body=file_metadata, media_body=media, fields="id, name")
                    .execute()
                )
                print(f"✅ Uploaded: {filename}")

            return True

        except HttpError as error:
            print(f"❌ Error uploading {filename}: {error}")
            return False

    def backup_folder(self, local_folder: str, drive_folder_id: str = None):
        """Backup all files from a local folder to Google Drive."""
        local_path = Path(local_folder)

        if not local_path.exists():
            print(f"❌ Local folder not found: {local_folder}")
            return

        if not local_path.is_dir():
            print(f"❌ Path is not a directory: {local_folder}")
            return

        # Create backup folder with timestamp (yyyymmddhhmm)
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d%H%M')}"
        target_folder_id = self.get_or_create_folder(backup_name, drive_folder_id)

        print(f"\n📂 Backing up: {local_folder}")
        print(f"📍 To Google Drive folder: {backup_name}\n")

        uploaded, failed = self._backup_folder_recursive(local_path, target_folder_id)

        print(f"\n{'=' * 50}")
        print(f"📊 Backup Summary:")
        print(f"   ✅ Uploaded: {uploaded}")
        print(f"   ❌ Failed: {failed}")
        print(f"{'=' * 50}")

    def _backup_folder_recursive(
        self, local_path: Path, parent_folder_id: str
    ) -> tuple[int, int]:
        """Recursively backup a folder structure. Returns (uploaded, failed) counts."""
        uploaded = 0
        failed = 0

        for item in local_path.iterdir():
            if item.is_file():
                if self.upload_file(str(item), parent_folder_id):
                    uploaded += 1
                else:
                    failed += 1
            elif item.is_dir():
                subfolder_id = self.get_or_create_folder(item.name, parent_folder_id)
                sub_uploaded, sub_failed = self._backup_folder_recursive(
                    item, subfolder_id
                )
                uploaded += sub_uploaded
                failed += sub_failed

        return uploaded, failed

    def list_backup_folders(self, parent_id: str = None) -> list[dict]:
        """List all backup folders (matching backup_* pattern) sorted by name descending."""
        query = "name contains 'backup_' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = (
            self.service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name, createdTime)",
                orderBy="name desc",
            )
            .execute()
        )

        return results.get("files", [])

    def delete_folder(self, folder_id: str, folder_name: str = ""):
        """Delete a folder from Google Drive (moves to trash)."""
        try:
            self.service.files().delete(fileId=folder_id).execute()
            print(f"🗑️  Deleted old backup: {folder_name}")
            return True
        except HttpError as error:
            print(f"❌ Error deleting {folder_name}: {error}")
            return False

    def cleanup_old_backups(self, parent_id: str = None, keep_count: int = 3):
        """Remove old backups, keeping only the most recent ones."""
        backups = self.list_backup_folders(parent_id)

        if len(backups) <= keep_count:
            print(
                f"📦 {len(backups)} backup(s) found, no cleanup needed (keeping {keep_count})"
            )
            return

        # Backups are sorted by name descending (newest first due to timestamp format)
        backups_to_delete = backups[keep_count:]

        print(f"\n🧹 Cleaning up old backups (keeping {keep_count} most recent)...")
        deleted_count = 0
        for backup in backups_to_delete:
            if self.delete_folder(backup["id"], backup["name"]):
                deleted_count += 1

        print(f"✅ Removed {deleted_count} old backup(s)")


def main():
    """Main entry point."""
    print("=" * 50)
    print("🚀 Auto Backup to Google Drive")
    print("=" * 50 + "\n")

    # Validate configuration
    if not BACKUP_FOLDER_PATH:
        print("❌ Error: BACKUP_FOLDER_PATH not set in .env file")
        print("Please create a .env file with the path to backup")
        sys.exit(1)

    # Initialize backup handler
    backup = GoogleDriveBackup()

    # Perform backup
    drive_folder_id = GOOGLE_DRIVE_FOLDER_ID if GOOGLE_DRIVE_FOLDER_ID else None
    backup.backup_folder(BACKUP_FOLDER_PATH, drive_folder_id)

    # Cleanup old backups, keep only 3 most recent
    backup.cleanup_old_backups(drive_folder_id, keep_count=3)

    print("\n✨ Backup complete!")


if __name__ == "__main__":
    main()
