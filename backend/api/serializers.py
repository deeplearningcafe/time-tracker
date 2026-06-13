from rest_framework import serializers
from django.contrib.auth import get_user_model
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .models import Project, TimeEntry, TimeTrack

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model. Handles user creation and retrieval.
    The password is write-only and is not included when serializing user
    data.
    """

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        """
        Creates and returns a new User instance, handling password hashing.
        """
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        return user


class ProjectSerializer(serializers.ModelSerializer):
    """
    Serializer for the Project model.
    """

    # The user is automatically set to the currently authenticated user.
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Project
        fields = ("id", "user", "title", "created_at", "color")
        read_only_fields = ("created_at",)

    # use custom validate over UniqueTogetherValidator to have more freedom
    def validate(self, data):
        request = self.context.get("request")
        title = data.get("title")
        if title:
            qs = Project.objects.filter(
                user=request.user, title=title, deleted_at__isnull=True
            )
            # if create is none else remove it for checking title
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"title": "You already have a project with this title."}
                )
        return data

    def validate_title(self, value):
        """
        If the provided title is a blank string, it is replaced with a
        default value 'No project'.
        """
        if value.strip() == "":
            return "No project"
        return value

    def validate_color(self, value):
        """
        If the provided color is a blank string, it is replaced with a
        default value 'No project'.
        """
        # if the # is included remove it
        if len(value.strip()) == 7:
            return value[1:]
        return value


class TimeEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for the TimeEntry model.
    """

    class Meta:
        model = TimeEntry
        fields = ("id", "project", "name", "created_at")
        read_only_fields = ("created_at",)
        # By explicitly defining an empty validators list, we override the
        # default behavior of ModelSerializer, which automatically creates
        # a UniqueTogetherValidator based on the model's 'constraints'.
        # This allows our custom `create` view logic in the ViewSet to
        # handle the "get_or_create" functionality without raising a
        # premature validation error for existing entries.
        validators = []

    def __init__(self, *args, **kwargs):
        """
        Dynamically filters the 'project' queryset to only show projects
        owned by the currently authenticated user. This prevents a user from
        assigning a time entry to another user's project.
        """
        super().__init__(*args, **kwargs)
        request = self.context.get("request", None)
        if request and hasattr(request, "user"):
            self.fields["project"].queryset = Project.objects.filter(
                user=request.user, deleted_at__isnull=True
            )

    def validate_name(self, value):
        """
        If the provided name is a blank string, it is replaced with a
        default value 'No name'.
        """
        if value.strip() == "":
            return "No name"
        return value


class TimeTrackSerializer(serializers.ModelSerializer):
    """
    Serializer for the TimeTrack model.
    """

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = TimeTrack
        fields = ("id", "time_entry", "user", "start_time", "end_time")

    def __init__(self, *args, **kwargs):
        """
        Dynamically filters the 'time_entry' queryset to only show entries
        owned by the currently authenticated user (via the project).
        """
        super().__init__(*args, **kwargs)
        request = self.context.get("request", None)
        if request and hasattr(request, "user"):
            self.fields["time_entry"].queryset = TimeEntry.objects.filter(
                project__user=request.user, deleted_at__isnull=True
            )

    def validate(self, data):
        """
        Validates the time track data to enforce business rules:
        1. The `end_time` must be chronologically after `start_time`.
        2. A user cannot start a new timer if one is already running.
        """
        # Combine instance data with incoming data to get the final state.
        instance_data = {}
        if self.instance:
            instance_data = {
                "start_time": self.instance.start_time,
                "end_time": self.instance.end_time,
                "user": self.instance.user,
            }

        final_data = {**instance_data, **data}
        start_time = final_data.get("start_time")
        end_time = final_data.get("end_time")
        user = final_data.get("user")

        if end_time and start_time and end_time <= start_time:
            raise serializers.ValidationError("End time must be after start time.")

        # Rule 2: Check for an existing running timer.
        # only performed when creating a NEW running timer.
        is_creating = self.instance is None
        is_running = end_time is None
        if is_creating and is_running:
            if TimeTrack.objects.filter(
                user=user, end_time__isnull=True, deleted_at__isnull=True
            ).exists():
                raise serializers.ValidationError(
                    "You already have a running time track."
                )

        return data


class DateRangeSerializer(serializers.Serializer):
    """
    Reusable serializer for validating date range query parameters.
    Accepts ISO 8601 formatted date-time strings and an optional timezone.
    """

    start_date = serializers.DateTimeField(
        required=False,
        help_text="Start datetime in ISO 8601 format (e.g. 2023-01-01T00:00:00Z)",
    )
    end_date = serializers.DateTimeField(
        required=False, help_text="End datetime in ISO 8601 format"
    )

    timezone = serializers.CharField(
        required=False,
        default="UTC",
        help_text="IANA timezone string (e.g. 'Asia/Tokyo')",
    )

    def validate_timezone(self, value):
        """
        Validates that the provided string is a valid IANA timezone.
        """
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError(f"Unknown timezone: {value}")
        return value

    def validate(self, data):
        """
        Check that the start_date is not after the end_date.
        """
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError("start_date cannot be after end_date.")
        return data


class ProjectImportSerializer(serializers.Serializer):
    """Serializer for validating a project object during import."""

    id = serializers.UUIDField(required=False)
    title = serializers.CharField(max_length=200)
    color = serializers.CharField(max_length=6)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(required=False)
    deleted_at = serializers.DateTimeField(required=False, allow_null=True)


class TimeEntryImportSerializer(serializers.Serializer):
    """Serializer for validating a time entry object during import."""

    id = serializers.UUIDField(required=False)
    project_id = serializers.UUIDField(required=False)
    name = serializers.CharField(max_length=255)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(required=False)
    deleted_at = serializers.DateTimeField(required=False, allow_null=True)


class TimeTrackImportSerializer(serializers.Serializer):
    """Serializer for validating a time track object during import."""

    id = serializers.UUIDField(required=False)
    time_entry_id = serializers.UUIDField(required=False)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False)
    deleted_at = serializers.DateTimeField(required=False, allow_null=True)


class DataImportSerializer(serializers.Serializer):
    """
    The main serializer for validating the entire data import JSON file.
    It ensures the top-level keys and the structure of their lists are
    correct. The actual database insertion logic is handled in the view.
    """

    projects = ProjectImportSerializer(many=True, required=False)
    time_entries = TimeEntryImportSerializer(many=True, required=False)
    time_tracks = TimeTrackImportSerializer(many=True, required=False)

    def validate(self, data):
        """
        Validates referential integrity of projects and time entries.
        """
        user = self.context.get("user")
        if not user:
            return data

        incoming_pids = {str(p["id"]) for p in data.get("projects", []) if "id" in p}
        incoming_tids = {
            str(te["id"]) for te in data.get("time_entries", []) if "id" in te
        }

        db_pids = set(Project.objects.filter(user=user).values_list("id", flat=True))
        db_pids_str = {str(pid) for pid in db_pids}
        all_valid_pids = incoming_pids.union(db_pids_str)

        # time entry pid must be on incoming or db pids
        for te in data.get("time_entries", []):
            proj_id = te.get("project_id")
            if proj_id and str(proj_id) not in all_valid_pids:
                raise serializers.ValidationError(
                    f"Invalid project reference: {proj_id}"
                )

        db_tids = set(
            TimeEntry.objects.filter(project__user=user).values_list("id", flat=True)
        )
        db_tids_str = {str(tid) for tid in db_tids}
        all_valid_tids = incoming_tids.union(db_tids_str)

        for tt in data.get("time_tracks", []):
            te_id = tt.get("time_entry_id")
            if te_id and str(te_id) not in all_valid_tids:
                raise serializers.ValidationError(
                    f"Invalid time entry reference: {te_id}"
                )

        return data
