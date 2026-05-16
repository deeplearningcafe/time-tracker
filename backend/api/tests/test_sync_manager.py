import os
import json
import shutil
import tempfile
from unittest import mock
from cryptography.fernet import Fernet
from django.test import TestCase
from django.contrib.auth import get_user_model
from api.sync_manager import SyncManager
from api.models import Project

User = get_user_model()


class SyncManagerLogicTest(TestCase):
    """
    Test suite for the SyncManager logic, covering file encryption,
    metadata handling, and database updates from sync files.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

        self.user = User.objects.create_user(username="sync_user", password="password")
        self.project = Project.objects.create(
            user=self.user, title="Local Project", color="FFFFFF"
        )

        self.key = Fernet.generate_key().decode()
        self.machine_id = "test_machine_1"

        # Mock environment variables to point to temp dir and use dummy key
        self.env_patcher = mock.patch.dict(
            os.environ,
            {
                "SYNC_DRIVE_PATH": self.test_dir,
                "MACHINE_ID": self.machine_id,
                "SYNC_SECRET_KEY": self.key,
            },
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_export_to_drive_creates_encrypted_files(self):
        """
        Ensure export creates 'data.enc' and 'meta.json', and that data is encrypted.
        """
        manager = SyncManager(self.user)
        manager.export_to_drive()

        data_path = os.path.join(self.test_dir, "data.enc")
        meta_path = os.path.join(self.test_dir, "meta.json")

        self.assertTrue(os.path.exists(data_path))
        self.assertTrue(os.path.exists(meta_path))

        with open(meta_path, "r") as f:
            meta = json.load(f)
        self.assertEqual(meta["machine_id"], self.machine_id)
        self.assertIn("timestamp", meta)

        with open(data_path, "rb") as f:
            content = f.read()

        # Attempting to parse as JSON should fail (it's encrypted bytes)
        with self.assertRaises(Exception):
            json.loads(content)

        f = Fernet(self.key)
        decrypted = f.decrypt(content)
        data = json.loads(decrypted)

        self.assertEqual(data["projects"][0]["title"], "Local Project")

    def test_should_download_logic(self):
        """
        Ensure download is only triggered if meta.json exists AND
        machine_id is different.
        """
        manager = SyncManager(self.user)
        meta_path = os.path.join(self.test_dir, "meta.json")

        # Case 1: No meta file -> Should not download
        self.assertFalse(manager.should_download())

        # Case 2: Meta file with SAME machine ID -> Should not download
        with open(meta_path, "w") as f:
            json.dump({"machine_id": self.machine_id, "timestamp": 12345}, f)
        self.assertFalse(manager.should_download())

        # Case 3: Meta file with DIFFERENT machine ID -> Should download
        with open(meta_path, "w") as f:
            json.dump({"machine_id": "other_machine", "timestamp": 12345}, f)
        self.assertTrue(manager.should_download())

    def test_import_from_drive_updates_db(self):
        """
        Ensure importing from drive decrypts data and replaces local DB state.
        """
        # 1. Prepare "remote" data (simulating another machine)
        import_data = {
            "projects": [
                {
                    "title": "Remote Project",
                    "color": "000000",
                    "created_at": "2023-01-01T00:00:00Z",
                }
            ],
            "time_entries": [],
            "time_tracks": [],
        }
        json_str = json.dumps(import_data)
        f = Fernet(self.key)
        encrypted = f.encrypt(json_str.encode())

        with open(os.path.join(self.test_dir, "data.enc"), "wb") as file:
            file.write(encrypted)

        manager = SyncManager(self.user)
        manager.import_from_drive()

        # 3. Verify DB state
        # Old project should be gone
        self.assertFalse(Project.objects.filter(title="Local Project").exists())
        # New project should exist
        self.assertTrue(Project.objects.filter(title="Remote Project").exists())

        # 4. Verify meta.json is updated to current machine ID
        # This prevents re-downloading on next restart
        with open(os.path.join(self.test_dir, "meta.json"), "r") as file:
            meta = json.load(file)
        self.assertEqual(meta["machine_id"], self.machine_id)
