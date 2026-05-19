import os
import json
import time
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
from .services import UserDataService
from .models import SyncState, TimeTrack, Project, TimeEntry
from .cloud_storage import RcloneAdapter


class SyncManager:
    """
    Manages the synchronization of user data to a local file system path.
    Handles encryption (Fernet) and metadata (meta.json) to avoid conflicts.
    """

    def __init__(self, user):
        self.user = user
        self.drive_path = os.environ.get("SYNC_DRIVE_PATH")
        self.machine_id = os.environ.get("MACHINE_ID", "generic_machine")
        self.key = os.environ.get("SYNC_SECRET_KEY")

        if not self.drive_path or not self.key:
            raise ValueError("SYNC_DRIVE_PATH and SYNC_SECRET_KEY must be set.")

        # the key is stored in str but it needs to be bytes
        # but it seems that str also works
        self.fernet = Fernet(self.key)
        self.meta_file = os.path.join(self.drive_path, "meta.json")
        self.current_name = "current"
        self.cache_name = "cache"
        self.current_dir = os.path.join(self.drive_path, self.current_name)
        self.cache_dir = os.path.join(self.drive_path, self.cache_name)

        os.makedirs(self.current_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

        remote_name = os.environ.get("REMOTE_NAME")
        remote_path = os.environ.get("REMOTE_PATH")
        self.storage = RcloneAdapter(remote_name, remote_path, self.drive_path)

    def _read_meta(self):
        if os.path.exists(self.meta_file):
            try:
                with open(self.meta_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"common": {}, "years": {}}

    def _write_meta(self, meta):
        with open(self.meta_file, "w") as f:
            json.dump(meta, f)

    def _encrypt_and_write(self, data_dict, filepath):
        json_str = json.dumps(data_dict)
        # fernet takes bytes as input and json.encode() is the bytes format
        encrypted_data = self.fernet.encrypt(json_str.encode())
        # wb flag is binary file
        with open(filepath, "wb") as f:
            f.write(encrypted_data)

    def _read_and_decrypt(self, filepath):
        if not os.path.exists(filepath):
            return {}
        with open(filepath, "rb") as f:
            encrypted_data = f.read()
        decrypted_data = self.fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())

    def pull_from_cloud(self):
        """Downloads meta.json, determines what changed, and downloads ONLY those files."""
        # Always pull the latest meta
        self.storage.download_file("meta.json")

        meta = self._read_meta()
        sync_state, _ = SyncState.objects.get_or_create(user=self.user)
        last_sync_ts = sync_state.last_sync_at.timestamp()

        # if modified by another machine and timestamp is newer
        c_meta = meta.get("common", {})
        if (
            c_meta.get("machine_id") != self.machine_id
            and c_meta.get("timestamp", 0) > last_sync_ts
        ):
            self.storage.download_file(f"{self.current_name}/common.enc")

        for year_str, y_meta in meta.get("years", {}).items():
            if (
                y_meta.get("machine_id") != self.machine_id
                and y_meta.get("timestamp", 0) > last_sync_ts
            ):
                year = int(year_str)
                current_year = timezone.now().year
                folder = self.current_name if year == current_year else self.cache_name
                self.storage.download_file(f"{folder}/tracks_{year}.enc")

    def push_to_cloud(self, files_to_upload):
        """Uploads specific files to the cloud."""
        for rel_path in files_to_upload:
            self.storage.upload_file(rel_path)

    def should_download(self):
        """
        Determines if the local data is outdated compared to the sync folder.
        Returns True if the last update was made by a DIFFERENT machine.
        """
        meta = self._read_meta()
        sync_state, _ = SyncState.objects.get_or_create(user=self.user)
        last_sync_ts = sync_state.last_sync_at.timestamp()

        c_meta = meta.get("common", {})
        if (
            c_meta.get("machine_id") != self.machine_id
            and c_meta.get("timestamp", 0) > last_sync_ts
        ):
            return True

        for year, y_meta in meta.get("years", {}).items():
            if (
                y_meta.get("machine_id") != self.machine_id
                and y_meta.get("timestamp", 0) > last_sync_ts
            ):
                return True
        return False

    def export_to_drive(self):
        """
        Exports user data, encrypts it, and writes it to the sync folder.
        Updates meta.json with the current machine ID.
        """
        sync_state, _ = SyncState.objects.get_or_create(user=self.user)
        last_sync = sync_state.last_sync_at
        now = timezone.now()
        current_year = now.year

        meta = self._read_meta()
        if "common" not in meta:
            meta["common"] = {}
        if "years" not in meta:
            meta["years"] = {}

        files_to_upload = ["meta.json"]

        common_modified = (
            Project.objects.filter(user=self.user, updated_at__gt=last_sync).exists()
            or TimeEntry.objects.filter(
                project__user=self.user, updated_at__gt=last_sync
            ).exists()
        )

        if common_modified or not meta["common"]:
            common_data = UserDataService.get_common_data_as_dict(self.user)
            # current_dir has the abs path
            self._encrypt_and_write(
                common_data, os.path.join(self.current_dir, "common.enc")
            )
            meta["common"] = {"timestamp": time.time(), "machine_id": self.machine_id}
            files_to_upload.append(f"{self.current_name}/common.enc")

        modified_years = set(
            TimeTrack.objects.filter(
                user=self.user, updated_at__gt=last_sync
            ).values_list("start_time__year", flat=True)
        )

        if str(current_year) not in meta["years"]:
            modified_years.add(current_year)

        for year in modified_years:
            if not year:
                continue
            year_str = str(year)
            tracks_data = UserDataService.get_tracks_data_as_dict(self.user, year)

            folder_name = self.current_name if year == current_year else self.cache_name
            filename = f"tracks_{year}.enc"

            local_filepath = os.path.join(self.drive_path, folder_name, filename)
            rel_filepath = f"{folder_name}/{filename}"

            self._encrypt_and_write(tracks_data, local_filepath)
            meta["years"][year_str] = {
                "timestamp": time.time(),
                "machine_id": self.machine_id,
            }
            files_to_upload.append(rel_filepath)

        self._write_meta(meta)
        sync_state.last_sync_at = now
        sync_state.save()

        return files_to_upload

    def import_from_drive(self):
        """
        Reads encrypted data from the sync folder, decrypts it, and imports it.
        """

        meta = self._read_meta()
        sync_state, _ = SyncState.objects.get_or_create(user=self.user)
        last_sync_ts = sync_state.last_sync_at.timestamp()

        c_meta = meta.get("common", {})
        # despite not changing it is imported again
        if (
            c_meta.get("machine_id") != self.machine_id
            and c_meta.get("timestamp", 0) > last_sync_ts
        ):
            common_path = os.path.join(self.current_dir, "common.enc")
            data = self._read_and_decrypt(common_path)
            if data:
                UserDataService.import_user_data(self.user, data)
            meta["common"]["machine_id"] = self.machine_id

        # only updated years are read
        for year_str, y_meta in meta.get("years", {}).items():
            if (
                y_meta.get("machine_id") != self.machine_id
                and y_meta.get("timestamp", 0) > last_sync_ts
            ):
                year = int(year_str)
                current_year = timezone.now().year
                folder = self.current_dir if year == current_year else self.cache_dir
                filepath = os.path.join(folder, f"tracks_{year}.enc")
                data = self._read_and_decrypt(filepath)
                if data:
                    UserDataService.import_user_data(self.user, data)
                y_meta["machine_id"] = self.machine_id

        self._write_meta(meta)

        sync_state, _ = SyncState.objects.get_or_create(user=self.user)
        sync_state.last_sync_at = timezone.now()
        sync_state.save()
