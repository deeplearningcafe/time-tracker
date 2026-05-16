from django.contrib import admin
from .models import Project, TimeEntry, TimeTrack


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "created_at")
    search_fields = ("title",)


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "created_at")
    search_fields = ("name",)


@admin.register(TimeTrack)
class TimeTrackAdmin(admin.ModelAdmin):
    list_display = ("time_entry", "user", "start_time", "end_time")
    search_fields = ("time_entry", "user", "start_time")
