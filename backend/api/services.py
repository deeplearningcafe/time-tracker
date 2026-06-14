import json
import csv
import io
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from .models import Project, TimeEntry, TimeTrack
from .serializers import DataImportSerializer


class UserDataService:
    """
    Service class to handle the extraction and insertion of user data.
    Used by both the DataPortabilityViewSet (API) and the SyncManager (Local Sync).
    """

    @staticmethod
    def parse_toggl_csv(csv_file, user):
        """
        Parses a Toggl Track CSV export and converts it to the app's modern JSON
        format by generating deterministic UUIDs. Assumes Europe/Madrid timezone
        for the local times.

        Args:
            csv_file: The uploaded CSV file object.
            user: User object from the database to link the data
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
            project_title = row.get("Project", "").strip() or "No project"
            entry_name = row.get("Description", "").strip() or "No name"

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

            # Generate Deterministic UUIDs to ensure idempotency
            project_id = str(
                uuid.uuid5(uuid.NAMESPACE_DNS, f"{user.id}-project-{project_title}")
            )
            entry_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_DNS, f"{user.id}-entry-{project_id}-{entry_name}"
                )
            )
            track_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    f"{user.id}-track-{entry_id}-{start_dt.isoformat()}",
                )
            )

            if project_title not in projects:
                projects[project_title] = {
                    "id": project_id,
                    "title": project_title,
                    "color": "000000",
                    "created_at": start_dt.isoformat(),
                    "updated_at": start_dt.isoformat(),
                }

            entry_key = (project_title, entry_name)
            if entry_key not in time_entries:
                time_entries[entry_key] = {
                    "id": entry_id,
                    "project_id": project_id,
                    "name": entry_name,
                    "created_at": start_dt.isoformat(),
                    "updated_at": start_dt.isoformat(),
                }

            time_tracks.append(
                {
                    "id": track_id,
                    "time_entry_id": entry_id,
                    "start_time": start_dt.isoformat(),
                    "end_time": end_dt.isoformat() if end_dt else None,
                    "updated_at": start_dt.isoformat(),
                }
            )

        return {
            "projects": list(projects.values()),
            "time_entries": list(time_entries.values()),
            "time_tracks": time_tracks,
        }

    @staticmethod
    def get_common_data_as_dict(user):
        projects = Project.objects.filter(user=user)
        time_entries = TimeEntry.objects.filter(project__user=user)
        return {
            "projects": [
                {
                    "id": str(p.id),
                    "title": p.title,
                    "color": p.color,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                    "deleted_at": p.deleted_at.isoformat() if p.deleted_at else None,
                }
                for p in projects
            ],
            "time_entries": [
                {
                    "id": str(te.id),
                    "project_id": str(te.project_id),
                    "name": te.name,
                    "created_at": te.created_at.isoformat(),
                    "updated_at": te.updated_at.isoformat(),
                    "deleted_at": te.deleted_at.isoformat() if te.deleted_at else None,
                }
                for te in time_entries
            ],
        }

    @staticmethod
    def get_tracks_data_as_dict(user, year):
        """
        Serializes all the time tracks for the given user and year.
        """
        time_tracks = TimeTrack.objects.filter(user=user, start_time__year=year)
        return {
            "time_tracks": [
                {
                    "id": str(tt.id),
                    "time_entry_id": str(tt.time_entry_id),
                    "start_time": tt.start_time.isoformat(),
                    "end_time": tt.end_time.isoformat() if tt.end_time else None,
                    "updated_at": tt.updated_at.isoformat(),
                    "deleted_at": tt.deleted_at.isoformat() if tt.deleted_at else None,
                }
                for tt in time_tracks
            ]
        }

    @staticmethod
    def get_user_data_as_dict(user, year=None):
        """
        Serializes all data for the given user into a dictionary.
        If year is provided, filters the data to include only tracks from that year,
        and the projects/entries associated with them or created in that year.
        """

        common = UserDataService.get_common_data_as_dict(user)
        if year and year != "all":
            tracks = UserDataService.get_tracks_data_as_dict(user, int(year))
        else:
            time_tracks = TimeTrack.objects.filter(user=user)
            tracks = {
                "time_tracks": [
                    {
                        "id": str(tt.id),
                        "time_entry_id": str(tt.time_entry_id),
                        "start_time": tt.start_time.isoformat(),
                        "end_time": tt.end_time.isoformat() if tt.end_time else None,
                        "updated_at": tt.updated_at.isoformat(),
                        "deleted_at": tt.deleted_at.isoformat()
                        if tt.deleted_at
                        else None,
                    }
                    for tt in time_tracks
                ]
            }
        return {**common, **tracks}

    @staticmethod
    def merge_parsed_data(data_list):
        """
        Merges multiple parsed data dictionaries into a single one.
        Projects and Time Entries are deduplicated keeping the oldest created_at.
        The duplicated sample with newest updated_at is kept.
        Time Tracks are simply appended.
        """
        merged_projects = {}
        merged_entries = {}
        merged_tracks = []

        for data in data_list:
            for p in data.get("projects", []):
                key = p.get("id")
                if key not in merged_projects:
                    merged_projects[key] = p
                else:
                    # check for legacy data
                    if p.get("updated_at") and merged_projects[key].get("updated_at"):
                        if p["updated_at"] > merged_projects[key]["updated_at"]:
                            merged_projects[key] = p
                    elif p["created_at"] < merged_projects[key]["created_at"]:
                        merged_projects[key]["created_at"] = p["created_at"]

            for te in data.get("time_entries", []):
                key = te.get("id")
                if key not in merged_entries:
                    merged_entries[key] = te
                else:
                    if te.get("updated_at") and merged_entries[key].get("updated_at"):
                        if te["updated_at"] > merged_entries[key]["updated_at"]:
                            merged_entries[key] = te
                    elif te["created_at"] < merged_entries[key]["created_at"]:
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
        serializer = DataImportSerializer(data=data, context={"user": user})
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            raise IntegrityError(f"Validation failed: {serializer.errors}")

        validated_data = serializer.validated_data

        # Maps incoming CSV UUIDs to existing Native UUIDs to prevent orphans
        id_mapping = {}

        with transaction.atomic():
            # LWW Merge (Delta Sync)
            for p_data in validated_data.get("projects", []):
                original_p_id = p_data["id"]
                updated_at = p_data.get("updated_at", timezone.now())

                p = Project.objects.filter(id=original_p_id).first()
                if not p:
                    # Check for title clash as different id
                    p = Project.objects.filter(
                        user=user, title=p_data["title"], deleted_at__isnull=True
                    ).first()

                if p:
                    id_mapping[original_p_id] = p.id
                    # Conflict Resolution (Last-Write-Wins)
                    if p.updated_at < updated_at:
                        Project.objects.filter(id=p.id).update(
                            title=p_data["title"],
                            color=p_data["color"],
                            updated_at=updated_at,
                            deleted_at=p_data.get("deleted_at"),
                        )
                else:
                    Project.objects.create(
                        id=original_p_id,
                        user=user,
                        title=p_data["title"],
                        color=p_data["color"],
                        created_at=p_data["created_at"],
                        updated_at=updated_at,
                        deleted_at=p_data.get("deleted_at"),
                    )

            for te_data in validated_data.get("time_entries", []):
                original_te_id = te_data["id"]
                actual_project_id = id_mapping.get(
                    te_data["project_id"], te_data["project_id"]
                )
                updated_at = te_data.get("updated_at", timezone.now())

                te = TimeEntry.objects.filter(id=original_te_id).first()
                if not te:
                    # Check for name + project clash
                    te = TimeEntry.objects.filter(
                        project_id=actual_project_id,
                        name=te_data["name"],
                        deleted_at__isnull=True,
                    ).first()

                if te:
                    id_mapping[original_te_id] = te.id
                    if te.updated_at < updated_at:
                        TimeEntry.objects.filter(id=te.id).update(
                            project_id=actual_project_id,
                            name=te_data["name"],
                            updated_at=updated_at,
                            deleted_at=te_data.get("deleted_at"),
                        )
                else:
                    TimeEntry.objects.create(
                        id=original_te_id,
                        project_id=actual_project_id,
                        name=te_data["name"],
                        created_at=te_data["created_at"],
                        updated_at=updated_at,
                        deleted_at=te_data.get("deleted_at"),
                    )

            for tt_data in validated_data.get("time_tracks", []):
                original_tt_id = tt_data["id"]
                actual_te_id = id_mapping.get(
                    tt_data["time_entry_id"], tt_data["time_entry_id"]
                )
                updated_at = tt_data.get("updated_at", timezone.now())

                tt = TimeTrack.objects.filter(id=original_tt_id).first()
                if not tt:
                    # avoid duplicates
                    tt = TimeTrack.objects.filter(
                        time_entry_id=actual_te_id,
                        start_time=tt_data["start_time"],
                        end_time=tt_data.get("end_time"),
                        deleted_at__isnull=True,
                    ).first()

                if tt:
                    if tt.updated_at < updated_at:
                        TimeTrack.objects.filter(id=tt.id).update(
                            time_entry_id=actual_te_id,
                            start_time=tt_data["start_time"],
                            end_time=tt_data.get("end_time"),
                            updated_at=updated_at,
                            deleted_at=tt_data.get("deleted_at"),
                        )
                else:
                    TimeTrack.objects.create(
                        id=original_tt_id,
                        user=user,
                        time_entry_id=actual_te_id,
                        start_time=tt_data["start_time"],
                        end_time=tt_data.get("end_time"),
                        updated_at=updated_at,
                        deleted_at=tt_data.get("deleted_at"),
                    )

    @staticmethod
    def delete_user_data(user):
        with transaction.atomic():
            TimeTrack.objects.filter(user=user).delete()
            TimeEntry.objects.filter(project__user=user).delete()
            Project.objects.filter(user=user).delete()
