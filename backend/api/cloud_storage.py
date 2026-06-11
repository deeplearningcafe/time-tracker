import subprocess
import os
import shutil


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

        # win
        env_rclone = os.environ.get("RCLONE_EXE_PATH")
        # linux
        which_rclone = shutil.which("rclone")
        if env_rclone and os.path.exists(env_rclone):
            self.rclone_cmd = env_rclone
        elif which_rclone:
            self.rclone_cmd = which_rclone
        else:
            self.rclone_cmd = "rclone"

    def download_file(self, rel_path):
        """Downloads a specific file from the remote to the local mount."""
        if not self.is_configured:
            return False

        local_rel = os.path.normpath(rel_path)
        local = os.path.join(self.local_base, local_rel)

        remote_rel = rel_path.replace(os.sep, "/")
        remote = f"{self.remote_base}/{remote_rel}"

        try:
            subprocess.run(
                [self.rclone_cmd, "copyto", remote, local],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # FileNotFoundError if rclone is not installed
            # CalledProcessError if the file doesn't exist
            print(f"Rclone FileNotFoundError for {remote}")
            return False

    def upload_file(self, rel_path):
        """Uploads a specific file from the local mount to the remote."""
        if not self.is_configured:
            return False

        local_rel = os.path.normpath(rel_path)
        local = os.path.join(self.local_base, local_rel)

        remote_rel = rel_path.replace(os.sep, "/")
        remote = f"{self.remote_base}/{remote_rel}"

        try:
            subprocess.run(
                [self.rclone_cmd, "copyto", local, remote],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Rclone upload error for {rel_path}: {e}")
            return False
