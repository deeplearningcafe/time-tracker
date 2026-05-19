import subprocess
import os


class RcloneAdapter:
    """
    Encapsulates the external rclone dependency.
    Provides a simple interface for targeted file transfers.
    """

    def __init__(self, remote_name, remote_path, local_mount):
        self.remote_base = (
            f"{remote_name}:{remote_path}" if remote_name and remote_path else None
        )
        self.local_base = local_mount
        self.is_configured = bool(self.remote_base)

    def download_file(self, rel_path):
        """Downloads a specific file from the remote to the local mount."""
        if not self.is_configured:
            return False

        remote = f"{self.remote_base}/{rel_path}"
        local = os.path.join(self.local_base, rel_path)
        os.makedirs(os.path.dirname(local), exist_ok=True)

        try:
            subprocess.run(
                ["rclone", "copyto", remote, local], check=True, capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # FileNotFoundError if rclone is not installed
            # CalledProcessError if the file doesn't exist
            return False

    def upload_file(self, rel_path):
        """Uploads a specific file from the local mount to the remote."""
        if not self.is_configured:
            return False

        local = os.path.join(self.local_base, rel_path)
        remote = f"{self.remote_base}/{rel_path}"

        try:
            subprocess.run(
                ["rclone", "copyto", local, remote], check=True, capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Rclone upload error for {rel_path}: {e}")
            return False
