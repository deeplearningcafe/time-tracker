import os
import json
import shutil
import tempfile
import datetime
import uuid
from unittest import mock
from cryptography.fernet import Fernet
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from api.models import SyncState
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

        common_path = os.path.join(self.test_dir, "current", "common.enc")
        meta_path = os.path.join(self.test_dir, "meta.json")

        self.assertTrue(os.path.exists(common_path))
        self.assertTrue(os.path.exists(meta_path))

        with open(meta_path, "r") as f:
            meta = json.load(f)
        self.assertEqual(meta["common"]["machine_id"], self.machine_id)
        self.assertIn("timestamp", meta["common"])

        with open(common_path, "rb") as f:
            content = f.read()

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

        # Set the local sync state
        sync_state, _ = SyncState.objects.get_or_create(user=self.user)
        sync_state.last_sync_at = timezone.datetime.fromtimestamp(
            10000, tz=datetime.timezone.utc
        )
        sync_state.save()

        # No meta file -> no download
        self.assertFalse(manager.should_download())

        # SAME machine ID -> no download
        with open(meta_path, "w") as f:
            json.dump(
                {"common": {"machine_id": self.machine_id, "timestamp": 20000}}, f
            )
        self.assertFalse(manager.should_download())

        # DIFFERENT machine ID but OLDER/EQUAL timestamp -> no download
        with open(meta_path, "w") as f:
            json.dump({"common": {"machine_id": "other_machine", "timestamp": 5000}}, f)
        self.assertFalse(manager.should_download())

        # DIFFERENT machine ID and NEWER timestamp -> download
        with open(meta_path, "w") as f:
            json.dump(
                {"common": {"machine_id": "other_machine", "timestamp": 20000}}, f
            )
        self.assertTrue(manager.should_download())

    def test_import_from_drive_updates_db(self):
        """
        Ensure importing from drive decrypts data and replaces local DB state.
        """
        # 1. Prepare "remote" data (simulating another machine)
        # with the id it uses the lww format
        import_data = {
            "projects": [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Remote Project",
                    "color": "000000",
                    "created_at": "2023-01-01T00:00:00Z",
                    "updated_at": "2023-01-01T00:00:00Z",
                }
            ],
            "time_entries": [],
            "time_tracks": [],
        }
        json_str = json.dumps(import_data)
        f = Fernet(self.key)
        encrypted = f.encrypt(json_str.encode())

        os.makedirs(os.path.join(self.test_dir, "current"), exist_ok=True)
        with open(os.path.join(self.test_dir, "current", "common.enc"), "wb") as file:
            file.write(encrypted)

        sync_state, _ = SyncState.objects.get_or_create(user=self.user)
        sync_state.last_sync_at = timezone.datetime.fromtimestamp(
            10000, tz=datetime.timezone.utc
        )
        sync_state.save()

        with open(os.path.join(self.test_dir, "meta.json"), "w") as file:
            json.dump(
                {"common": {"machine_id": "other_machine", "timestamp": 12345}}, file
            )

        manager = SyncManager(self.user)
        manager.import_from_drive()

        # LWW Merge does not delete the old project, it just adds the new one
        self.assertTrue(Project.objects.filter(title="Local Project").exists())
        self.assertTrue(Project.objects.filter(title="Remote Project").exists())

        with open(os.path.join(self.test_dir, "meta.json"), "r") as file:
            meta = json.load(file)
        self.assertEqual(meta["common"]["machine_id"], self.machine_id)
