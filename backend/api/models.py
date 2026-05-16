from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

# Get the currently active User model
User = get_user_model()


class Project(models.Model):
    """
    Represents a user-defined project to categorize time entries.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(default=timezone.now)
    color = models.CharField(max_length=6, default="000000")

    class Meta:
        ordering = ["title"]
        constraints = [
            # A user cannot have two projects with the same title.
            models.UniqueConstraint(
                fields=["user", "title"], name="unique_project_title_per_user"
            )
        ]

    def __str__(self):
        return self.title


class TimeEntry(models.Model):
    """
    Represents a specific task or activity within a project.
    """

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="time_entries"
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]
        constraints = [
            # A project cannot have two time entries with the same name.
            models.UniqueConstraint(
                fields=["project", "name"], name="unique_time_entry_name_per_project"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.project.title})"


class TimeTrack(models.Model):
    """
    Represents a single, continuous block of time spent on a TimeEntry.
    If 'end_time' is NULL, the track is considered to be running.
    """

    time_entry = models.ForeignKey(
        TimeEntry, on_delete=models.CASCADE, related_name="time_tracks"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="time_tracks")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    def clean(self):
        """
        Adds model-level validation to be called by forms or serializers.
        """
        # This validation ensures data consistency by checking that the user
        # logging the time is the actual owner of the project.
        if self.user_id != self.time_entry.project.user_id:
            raise ValidationError(
                "The user of the time track must be the same as the "
                "owner of the project."
            )

    class Meta:
        # Order by most recent start time by default.
        ordering = ["-start_time"]
        constraints = [
            # Ensures a user can only have one running timer at a time.
            # This constraint is applied only to rows where end_time is NULL.
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(end_time__isnull=True),
                name="unique_running_timer_per_user",
            ),
            # Ensures that if an end_time is set, it must be after the
            # start_time. The check allows end_time to be NULL.
            models.CheckConstraint(
                condition=(Q(end_time__isnull=True) | Q(end_time__gt=F("start_time"))),
                name="end_time_after_start_time",
            ),
        ]

    def __str__(self):
        return f"Track for {self.time_entry.name} by {self.user.username}"
