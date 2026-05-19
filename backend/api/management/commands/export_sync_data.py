from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.sync_manager import SyncManager
import os

User = get_user_model()


class Command(BaseCommand):
    help = "Exports user data to the sync folder (encrypted)"

    def add_arguments(self, parser):
        parser.add_argument("--user", type=str, help="Username to export data for")

    def handle(self, *args, **options):
        username = options.get("user")

        # If no user provided, try to find one from env or pick the first superuser
        if not username:
            username = os.environ.get("SYNC_DEFAULT_USER")

        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'User "{username}" not found'))
                return
        else:
            # Fallback for single-user local apps: pick the first user
            user = User.objects.first()
            if not user:
                self.stderr.write(self.style.ERROR("No users found in database"))
                return

        try:
            manager = SyncManager(user)
            files_to_upload = manager.export_to_drive()
            manager.push_to_cloud(files_to_upload)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully exported data for {user.username} to {manager.drive_path}"
                )
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Export failed: {str(e)}"))
