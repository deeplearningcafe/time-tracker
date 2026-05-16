import json
import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo
from django.db import transaction
from django.db.models import Q
from .models import Project, TimeEntry, TimeTrack
from .serializers import DataImportSerializer


class UserDataService:
    """
    Service class to handle the extraction and insertion of user data.
    Used by both the DataPortabilityViewSet (API) and the SyncManager (Local Sync).
    """

    @staticmethod
    def parse_toggl_csv(csv_file):
        """
        Parses a Toggl Track CSV export and converts it to the app's JSON
        format. Assumes Europe/Madrid timezone for the local times.

        Args:
            csv_file: The uploaded CSV file object.
        Returns:
            dict: The parsed data in the application's JSON structure.
        """
        content = csv_file.read()
        try:
            decoded_file = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            decoded_file = content.decode("utf-8")

        reader = csv.DictReader(io.StringIO(decoded_file))

        projects = {}
        time_entries = {}
        time_tracks = []

        tz = ZoneInfo("Europe/Madrid")

        rows = list(reader)
        # Sort oldest to newest based on start date and time for correct IDs
        rows.sort(key=lambda x: (x.get("Start date", ""), x.get("Start time", "")))

        for row in rows:
            project_title = row.get("Project", "").strip()
            if not project_title:
                project_title = "No project"

            entry_name = row.get("Description", "").strip()
            if not entry_name:
                entry_name = "No name"

            start_date_str = row.get("Start date", "").strip()
            start_time_str = row.get("Start time", "").strip()
            end_date_str = row.get("End date", "").strip()
            end_time_str = row.get("End time", "").strip()

            start_dt = None
            if start_date_str and start_time_str:
                try:
                    start_dt_naive = datetime.strptime(
                        f"{start_date_str} {start_time_str}", "%Y-%m-%d %H:%M:%S"
                    )
                    start_dt = start_dt_naive.replace(tzinfo=tz)
                except ValueError:
                    continue

            end_dt = None
            if end_date_str and end_time_str:
                try:
                    end_dt_naive = datetime.strptime(
                        f"{end_date_str} {end_time_str}", "%Y-%m-%d %H:%M:%S"
                    )
                    end_dt = end_dt_naive.replace(tzinfo=tz)
                except ValueError:
                    pass

            if not start_dt:
                continue

            if project_title not in projects:
                projects[project_title] = {
                    "title": project_title,
                    "color": "000000",
                    "created_at": start_dt.isoformat(),
                }

            entry_key = (project_title, entry_name)
            if entry_key not in time_entries:
                time_entries[entry_key] = {
                    "project_title": project_title,
                    "name": entry_name,
                    "created_at": start_dt.isoformat(),
                }

            time_tracks.append(
                {
                    "entry_project_title": project_title,
                    "entry_name": entry_name,
                    "start_time": start_dt.isoformat(),
                    "end_time": end_dt.isoformat() if end_dt else None,
                }
            )

        return {
            "projects": list(projects.values()),
            "time_entries": list(time_entries.values()),
            "time_tracks": time_tracks,
        }

    @staticmethod
    def get_user_data_as_dict(user, year=None):
        """
        Serializes all data for the given user into a dictionary.
        If year is provided, filters the data to include only tracks from that year,
        and the projects/entries associated with them or created in that year.
        """
        if year:
            try:
                year = int(year)
            except ValueError:
                year = None

        if year:
            # Filter tracks by start_time year
            time_tracks = TimeTrack.objects.filter(user=user, start_time__year=year)

            track_entry_ids = time_tracks.values_list(
                "time_entry_id", flat=True
            ).distinct()

            # if created this year but no data does it make sense to include?
            # Include entries created in this year OR used in this year's tracks
            time_entries = TimeEntry.objects.filter(
                Q(project__user=user)
                & (Q(created_at__year=year) | Q(id__in=track_entry_ids))
            ).distinct()

            entry_project_ids = time_entries.values_list(
                "project_id", flat=True
            ).distinct()

            # Include projects created in this year OR used in this year's entries
            projects = Project.objects.filter(
                Q(user=user) & (Q(created_at__year=year) | Q(id__in=entry_project_ids))
            ).distinct()
        else:
            projects = Project.objects.filter(user=user)
            time_entries = TimeEntry.objects.filter(project__user=user)
            time_tracks = TimeTrack.objects.filter(user=user)

        return {
            "projects": [
                {
                    "title": p.title,
                    "color": p.color,
                    "created_at": p.created_at.isoformat(),
                }
                for p in projects
            ],
            "time_entries": [
                {
                    "project_title": te.project.title,
                    "name": te.name,
                    "created_at": te.created_at.isoformat(),
                }
                for te in time_entries
            ],
            "time_tracks": [
                {
                    "entry_project_title": tt.time_entry.project.title,
                    "entry_name": tt.time_entry.name,
                    "start_time": tt.start_time.isoformat(),
                    "end_time": (tt.end_time.isoformat() if tt.end_time else None),
                }
                for tt in time_tracks
            ],
        }

    @staticmethod
    def merge_parsed_data(data_list):
        """
        Merges multiple parsed data dictionaries into a single one.
        Projects and Time Entries are deduplicated keeping the oldest created_at.
        Time Tracks are simply appended.
        """
        merged_projects = {}
        merged_entries = {}
        merged_tracks = []

        for data in data_list:
            for p in data.get("projects", []):
                title = p["title"]
                if title not in merged_projects:
                    merged_projects[title] = p
                else:
                    if p["created_at"] < merged_projects[title]["created_at"]:
                        merged_projects[title]["created_at"] = p["created_at"]

            for te in data.get("time_entries", []):
                key = (te["project_title"], te["name"])
                if key not in merged_entries:
                    merged_entries[key] = te
                else:
                    if te["created_at"] < merged_entries[key]["created_at"]:
                        merged_entries[key]["created_at"] = te["created_at"]

            merged_tracks.extend(data.get("time_tracks", []))

        return {
            "projects": list(merged_projects.values()),
            "time_entries": list(merged_entries.values()),
            "time_tracks": merged_tracks,
        }

    @staticmethod
    def import_user_data(user, data):
        """
        Replaces the user's data with the provided dictionary.
        Executes within a transaction to ensure integrity.
        """
        serializer = DataImportSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        with transaction.atomic():
            # 1. Clear existing data for the user.
            Project.objects.filter(user=user).delete()

            projects_to_create = [
                Project(
                    user=user,
                    title=p["title"],
                    color=p["color"],
                    created_at=p["created_at"],
                )
                for p in validated_data.get("projects", [])
            ]
            Project.objects.bulk_create(projects_to_create)
            projects_map = {p.title: p for p in Project.objects.filter(user=user)}

            entries_to_create = [
                TimeEntry(
                    project=projects_map[te["project_title"]],
                    name=te["name"],
                    created_at=te["created_at"],
                )
                for te in validated_data.get("time_entries", [])
            ]
            TimeEntry.objects.bulk_create(entries_to_create)

            # Map entries by (Project Title, Entry Name) tuple
            entries_map = {
                (te.project.title, te.name): te
                for te in TimeEntry.objects.filter(project__user=user)
            }

            tracks_to_create = []
            for tt in validated_data.get("time_tracks", []):
                key = (tt["entry_project_title"], tt["entry_name"])
                if key in entries_map:
                    tracks_to_create.append(
                        TimeTrack(
                            user=user,
                            time_entry=entries_map[key],
                            start_time=tt["start_time"],
                            end_time=tt.get("end_time"),
                        )
                    )
            TimeTrack.objects.bulk_create(tracks_to_create)
