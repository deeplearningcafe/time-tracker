import json
from collections import defaultdict
from datetime import timedelta
from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Max, Sum, DurationField, Q, ExpressionWrapper
from django.db.models.functions import TruncDate
from django.db.models.functions import ExtractYear
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Project, TimeEntry, TimeTrack
from .serializers import (
    DataImportSerializer,
    ProjectSerializer,
    DateRangeSerializer,
    TimeEntrySerializer,
    TimeTrackSerializer,
    UserSerializer,
)
from .services import UserDataService
from .sync_manager import SyncManager

User = get_user_model()


class UserViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Secure API endpoint for user registration and retrieval.
    - POST /api/users/: Creates a new user (registration).
    - GET /api/users/me/: Retrieves the current authenticated user's details.
    This viewset intentionally avoids ModelViewSet to prevent exposing list
    or detail endpoints for all users.
    """

    serializer_class = UserSerializer
    # No queryset is defined to prevent accidental exposure of user data.
    queryset = User.objects.none()
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        """
        Allow anyone to create a user (register), but require
        authentication for all other actions.
        """
        if self.action == "create":
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"])
    def me(self, request):
        """
        Custom action to retrieve the authenticated user's own information.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows projects to be viewed or edited. Ensures users
    can only access their own projects.
    """

    serializer_class = ProjectSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This view returns a list of all projects owned by the currently
        authenticated user.
        """
        return Project.objects.filter(user=self.request.user, deleted_at__isnull=True)

    def perform_destroy(self, instance):
        """
        Implements cascade on delete for soft deletes
        """
        now = timezone.now()
        instance.deleted_at = now
        instance.save()
        TimeEntry.objects.filter(project=instance, deleted_at__isnull=True).update(
            deleted_at=now
        )
        TimeTrack.objects.filter(
            time_entry__project=instance, deleted_at__isnull=True
        ).update(deleted_at=now)

    @action(detail=False, methods=["get"])
    def durations(self, request):
        """
        Returns a dictionary of project IDs and their total tracked
        duration in seconds.
        """
        tracks = (
            TimeTrack.objects.filter(
                user=request.user,
                end_time__isnull=False,
                time_entry__project__isnull=False,
                deleted_at__isnull=True,
                time_entry__deleted_at__isnull=True,
                time_entry__project__deleted_at__isnull=True,
            )
            .values("time_entry__project")
            .annotate(
                total_duration=Sum(
                    ExpressionWrapper(
                        F("end_time") - F("start_time"), output_field=DurationField()
                    )
                )
            )
        )

        durations_map = {}
        for t in tracks:
            project_id = t["time_entry__project"]
            duration = t["total_duration"]
            durations_map[str(project_id)] = duration.total_seconds() if duration else 0

        return Response(durations_map)


class TimeEntryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for time entries. Includes a custom action to retrieve
    recently used entries.
    """

    serializer_class = TimeEntrySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This view returns time entries belonging to projects of the
        currently authenticated user.
        """
        return TimeEntry.objects.filter(
            project__user=self.request.user, deleted_at__isnull=True
        )

    def perform_destroy(self, instance):
        """
        Implements cascade on delete for soft deletes
        """
        now = timezone.now()
        instance.deleted_at = now
        instance.save()
        TimeTrack.objects.filter(time_entry=instance, deleted_at__isnull=True).update(
            deleted_at=now
        )

    def create(self, request, *args, **kwargs):
        """
        Overrides the default create behavior to prevent duplicate entries.
        If a time entry with the same name and project already exists,
        it returns the existing entry (get). Otherwise, it creates a new
        one (create).
        """
        print(f"Data {request.data}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project_id = serializer.validated_data.get("project").id
        print(f"project_id {project_id}")
        try:
            project = Project.objects.get(
                pk=project_id, user=request.user, deleted_at__isnull=True
            )
        except Project.DoesNotExist:
            return Response(
                {"project": "Invalid project ID."}, status=status.HTTP_400_BAD_REQUEST
            )

        time_entry, created = TimeEntry.objects.get_or_create(
            name=serializer.validated_data.get("name"),
            project=project,
            deleted_at__isnull=True,
        )

        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        response_serializer = self.get_serializer(time_entry)
        return Response(response_serializer.data, status=status_code)

    def update(self, request, *args, **kwargs):
        """
        Updates a time entry. Handles merging if the update would cause a
        duplicate entry (same name in the same project).
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        # We need to manually validate project ownership and check for duplicates
        # before calling the standard serializer save, because we might need to merge.

        data = request.data
        new_project_id = data.get("project")
        new_name = data.get("name", instance.name)

        if new_project_id:
            try:
                new_project = Project.objects.get(
                    pk=new_project_id, user=request.user, deleted_at__isnull=True
                )
            except Project.DoesNotExist:
                return Response(
                    {"project": "Invalid project ID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if a DIFFERENT entry already exists with this target configuration
            existing_target = (
                TimeEntry.objects.filter(
                    project=new_project, name=new_name, deleted_at__isnull=True
                )
                .exclude(pk=instance.pk)
                .first()
            )

            if existing_target:
                # MERGE SCENARIO
                # 1. Move all tracks from current instance to existing_target
                with transaction.atomic():
                    TimeTrack.objects.filter(time_entry=instance).update(
                        time_entry=existing_target
                    )
                    instance.deleted_at = timezone.now()
                    instance.save()

                # 3. Return the existing_target data
                serializer = self.get_serializer(existing_target)
                return Response(serializer.data)

        # STANDARD UPDATE SCENARIO
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """
        Retrieves a list of time entries for the authenticated user,
        filtered by a optional date range. Filters entries based on
        any time track overlapping with the requested ISO date range.

        Query Parameters:
        - `start_date` (ISO 8601 format): The start of the date range.
        - `end_date` (ISO 8601 format): The end of the date range.
        """
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        params = serializer.validated_data
        start_date = params.get("start_date")
        end_date = params.get("end_date")

        # if no date range return recent ones
        if not start_date and not end_date:
            return self.recent(request)

        queryset = self.get_queryset()

        # Standard Overlap Formula: StartA < EndB AND EndA > StartB
        if start_date and end_date:
            queryset = queryset.filter(
                Q(time_tracks__start_time__lt=end_date)
                & (
                    Q(time_tracks__end_time__gt=start_date)
                    | Q(time_tracks__end_time__isnull=True)
                )
                & Q(time_tracks__deleted_at__isnull=True)
            ).distinct()
        elif start_date:
            queryset = queryset.filter(
                (
                    Q(time_tracks__end_time__gt=start_date)
                    | Q(time_tracks__end_time__isnull=True)
                )
                & Q(time_tracks__deleted_at__isnull=True)
            ).distinct()
        elif end_date:
            queryset = queryset.filter(
                time_tracks__start_time__lt=end_date,
                time_tracks__deleted_at__isnull=True,
            ).distinct()

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def recent(self, request):
        """
        Returns unique time entries tracked in the last 30 days, ordered
        by the most recently tracked, using an efficient database query.
        """
        thirty_days_ago = timezone.now() - timedelta(days=30)

        queryset = (
            self.get_queryset()
            .filter(
                time_tracks__start_time__gte=thirty_days_ago,
                time_tracks__deleted_at__isnull=True,
            )
            .annotate(most_recent_track=Max("time_tracks__start_time"))
            .order_by("-most_recent_track")
        )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TimeTrackViewSet(viewsets.ModelViewSet):
    """
    API endpoint for time tracks. Includes a custom action to retrieve the
    currently running track.
    """

    serializer_class = TimeTrackSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This view returns a list of all time tracks for the currently
        authenticated user.
        """
        return TimeTrack.objects.filter(user=self.request.user, deleted_at__isnull=True)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    def list(self, request, *args, **kwargs):
        """
        Retrieves a list of time tracks for the authenticated user,
        filtered by a optional date range.

        Query Parameters:
        - `start_date` (ISO 8601 format): The start of the date range.
        - `end_date` (ISO 8601 format): The end of the date range.
        """
        # 1. Validate Query Parameters
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        params = serializer.validated_data
        start_date = params.get("start_date")
        end_date = params.get("end_date")

        queryset = self.get_queryset()

        # Standard Overlap Formula: StartA < EndB AND EndA > StartB
        if start_date and end_date:
            queryset = queryset.filter(
                Q(start_time__lt=end_date)
                & (Q(end_time__gt=start_date) | Q(end_time__isnull=True))
            )
        elif start_date:
            queryset = queryset.filter(
                Q(end_time__gt=start_date) | Q(end_time__isnull=True)
            )
        elif end_date:
            queryset = queryset.filter(start_time__lt=end_date)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def live(self, request):
        """
        Retrieves the currently running time track for the user, if one
        exists.
        """
        try:
            live_track = self.get_queryset().get(end_time__isnull=True)
            serializer = self.get_serializer(live_track)
            return Response(serializer.data)
        except TimeTrack.DoesNotExist:
            return Response(status=status.HTTP_204_NO_CONTENT)


class SummaryViewSet(viewsets.ViewSet):
    """
    API endpoint for retrieving aggregated time tracking data.
    GET /api/summary/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Returns a summary of time tracked within a date range, grouped by
        date, project, and time entry. Multi-day tracks are correctly
        split across midnight boundaries.
        """
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        tz_name = data.get("timezone", "UTC")
        user_tz = ZoneInfo(tz_name)

        if not start_date or not end_date:
            return Response(
                {"error": "Both start_date and end_date are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Group by Date, Project, and Time Entry.
        # We filter out running timers (end_time__isnull=False)
        summary_query = (
            TimeTrack.objects.filter(
                user=request.user,
                end_time__isnull=False,
                deleted_at__isnull=True,
                time_entry__deleted_at__isnull=True,
                time_entry__project__deleted_at__isnull=True,
            )
            .filter(Q(start_time__lt=end_date) & Q(end_time__gt=start_date))
            .select_related("time_entry__project")
        )

        aggregated_data = defaultdict(float)

        for track in summary_query:
            start_dt = track.start_time.astimezone(user_tz)
            end_dt = track.end_time.astimezone(user_tz)

            req_start = start_date.astimezone(user_tz)
            req_end = end_date.astimezone(user_tz)

            actual_start = max(start_dt, req_start)
            actual_end = min(end_dt, req_end)

            if actual_start >= actual_end:
                continue

            current_dt = actual_start
            while current_dt < actual_end:
                # Calculate the bounds of the current day segment
                next_day = (current_dt + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                segment_end = min(actual_end, next_day)
                duration = (segment_end - current_dt).total_seconds()

                date_str = current_dt.strftime("%Y-%m-%d")

                proj = track.time_entry.project if track.time_entry else None
                project_title = proj.title if proj else "No project"
                project_color = proj.color if proj else "808080"
                entry_name = track.time_entry.name if track.time_entry else "No name"

                key = (date_str, project_title, project_color, entry_name)
                aggregated_data[key] += duration

                current_dt = segment_end

        # Format the result as a flat list of daily entry summaries.
        # 1. Bar Charts (group by date)
        # 2. Pie Charts (group by project)
        # 3. Breakdown Lists (group by project -> entry)
        response_data = [
            {
                "date": key[0],
                "project": key[1],
                "project_color": key[2],
                "time_entry": key[3],
                "duration_seconds": duration,
            }
            for key, duration in aggregated_data.items()
        ]

        response_data.sort(key=lambda x: (x["date"], x["project"], x["time_entry"]))

        return Response(response_data)


class DataPortabilityViewSet(viewsets.ViewSet):
    """
    API endpoint for exporting and importing user data.
    - GET /api/data/available-years/
    - GET /api/data/export/
    - POST /api/data/import-data/
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="available-years")
    def available_years(self, request):
        """
        Returns a list of unique years where the user has data.
        """
        user = request.user
        track_years = (
            TimeTrack.objects.filter(user=user, deleted_at__isnull=True)
            .annotate(year=ExtractYear("start_time"))
            .values_list("year", flat=True)
            .distinct()
        )

        project_years = (
            Project.objects.filter(user=user, deleted_at__isnull=True)
            .annotate(year=ExtractYear("created_at"))
            .values_list("year", flat=True)
            .distinct()
        )

        years = set()
        for y in track_years:
            if y:
                years.add(int(y))
        for y in project_years:
            if y:
                years.add(int(y))

        return Response(sorted(list(years), reverse=True))

    @action(detail=False, methods=["get"])
    def export(self, request):
        """
        Serializes all data for the authenticated user and returns it as a
        file download.
        """

        year = request.query_params.get("year")
        export_data = UserDataService.get_user_data_as_dict(request.user, year=year)

        response = JsonResponse(
            export_data, json_dumps_params={"ensure_ascii": False, "indent": 4}
        )

        filename = (
            f"time_tracker_export_{year}.json"
            if year and year != "all"
            else "time_tracker_export.json"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=["post"], url_path="import-data")
    def import_data(self, request):
        """
        Imports data from an uploaded file (JSON or CSV), replacing all
        existing data for the user inside a single database transaction.
        """
        user = request.user

        # Accept multiple files
        import_files = request.FILES.getlist("files")
        if not import_files:
            # Fallback for single file upload
            import_files = request.FILES.getlist("file")

        if not import_files:
            return Response(
                {"error": "No files provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            parsed_data_list = []
            for import_file in import_files:
                if import_file.name.lower().endswith(".csv"):
                    parsed_data_list.append(
                        UserDataService.parse_toggl_csv(import_file)
                    )
                else:
                    parsed_data_list.append(
                        json.loads(import_file.read().decode("utf-8"))
                    )

            merged_data = UserDataService.merge_parsed_data(parsed_data_list)

            UserDataService.import_user_data(user, merged_data)

        except KeyError as e:
            return Response(
                {"error": f"Data integrity error: Missing reference {e}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except json.JSONDecodeError:
            return Response(
                {"error": "Malformed JSON file."}, status=status.HTTP_400_BAD_REQUEST
            )
        except UnicodeDecodeError:
            return Response(
                {"error": "Invalid file encoding. Please use UTF-8."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class SyncViewSet(viewsets.ViewSet):
    """
    API endpoint for handling the automatic synchronization logic.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def trigger_upload(self, request):
        """
        Manual trigger for uploading data to the sync folder.
        Used by the 'Synchronize' button in the sidebar.
        """
        try:
            manager = SyncManager(request.user)
            files_to_upload = manager.export_to_drive()
            manager.push_to_cloud(files_to_upload)
            return Response({"status": "synced"}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def startup_check(self, request):
        """
        Called on app startup. Checks if the sync folder has newer data.
        If so, imports it.
        """
        try:
            manager = SyncManager(request.user)
            manager.pull_from_cloud()

            if manager.should_download():
                manager.import_from_drive()
                return Response({"status": "downloaded"}, status=status.HTTP_200_OK)
            return Response({"status": "up_to_date"}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Sync error: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
