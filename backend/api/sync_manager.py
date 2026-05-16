import os
import json
import time
from cryptography.fernet import Fernet
from django.conf import settings
from .services import UserDataService


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
        self.data_file = os.path.join(self.drive_path, "data.enc")
        self.meta_file = os.path.join(self.drive_path, "meta.json")

        os.makedirs(self.drive_path, exist_ok=True)

    def should_download(self):
        """
        Determines if the local data is outdated compared to the sync folder.
        Returns True if the last update was made by a DIFFERENT machine.
        """
        if not os.path.exists(self.meta_file):
            return False

        try:
            with open(self.meta_file, "r") as f:
                meta = json.load(f)

            # If the machine ID in the file is different from ours, we assume
            # it's a newer update from another computer.
            if meta.get("machine_id") != self.machine_id:
                return True
            return False
        except Exception as e:
            print(f"Error reading meta file: {e}")
            return False

    def export_to_drive(self):
        """
        Exports user data, encrypts it, and writes it to the sync folder.
        Updates meta.json with the current machine ID.
        """
        raw_data = UserDataService.get_user_data_as_dict(self.user)
        json_str = json.dumps(raw_data)

        # fernet takes bytes as input and json.encode() is the bytes format
        encrypted_data = self.fernet.encrypt(json_str.encode())

        # wb flag is binary file
        with open(self.data_file, "wb") as f:
            f.write(encrypted_data)

        meta = {"machine_id": self.machine_id, "timestamp": time.time()}
        with open(self.meta_file, "w") as f:
            json.dump(meta, f)

    def import_from_drive(self):
        """
        Reads encrypted data from the sync folder, decrypts it, and imports it.
        """
        if not os.path.exists(self.data_file):
            return

        try:
            with open(self.data_file, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = self.fernet.decrypt(encrypted_data)
            data_dict = json.loads(decrypted_data.decode())

            UserDataService.import_user_data(self.user, data_dict)

            # Update meta.json to reflect that we are now in sync
            meta = {"machine_id": self.machine_id, "timestamp": time.time()}
            with open(self.meta_file, "w") as f:
                json.dump(meta, f)

        except Exception as e:
            print(f"Error importing from drive: {e}")
            raise e
