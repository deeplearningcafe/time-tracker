from datetime import timedelta
from datetime import timezone as dt_timezone
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Project, TimeEntry, TimeTrack

User = get_user_model()


class TestSummaryAPI(APITestCase):
    """
    Test suite for the Data Summarization endpoint:
    GET /api/summary/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    """

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.other_user = User.objects.create_user(
            username="other", password="password"
        )
        self.url = reverse("summary-list")

        self.project_a = Project.objects.create(
            user=self.user, title="Project A", color="FF0000"
        )
        self.project_b = Project.objects.create(
            user=self.user, title="Project B", color="00FF00"
        )

        self.entry_a1 = TimeEntry.objects.create(project=self.project_a, name="Task A1")
        self.entry_b1 = TimeEntry.objects.create(project=self.project_b, name="Task B1")

        # Reference time: 2025-09-15 12:00:00 UTC (Monday)
        self.ref_date = timezone.datetime(2025, 9, 15, 12, 0, 0, tzinfo=dt_timezone.utc)

        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_a1,
            start_time=self.ref_date,
            end_time=self.ref_date + timedelta(hours=1),
        )

        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_a1,
            start_time=self.ref_date + timedelta(hours=2),
            end_time=self.ref_date + timedelta(hours=2, minutes=30),
        )

        day_2 = self.ref_date + timedelta(days=1)
        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_b1,
            start_time=day_2,
            end_time=day_2 + timedelta(hours=2),
        )

        # 4. Running Track (Live) - Should be EXCLUDED
        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_a1,
            start_time=timezone.now(),
            end_time=None,
        )

        p_other = Project.objects.create(user=self.other_user, title="Other P")
        e_other = TimeEntry.objects.create(project=p_other, name="Other E")
        TimeTrack.objects.create(
            user=self.other_user,
            time_entry=e_other,
            start_time=self.ref_date,
            end_time=self.ref_date + timedelta(hours=5),
        )

    def test_summary_aggregation_success(self):
        """
        Verify that the endpoint correctly aggregates data by date, project,
        and time entry, summing up the durations.
        """
        self.client.force_authenticate(user=self.user)

        start = "2025-09-15T00:00:30+05:30"
        end = "2025-09-16T23:59:30+05:30"

        response = self.client.get(self.url, {"start_date": start, "end_date": end})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # We expect 2 items in the list:
        # 1. Day 1, Project A, Task A1 (1h + 30m = 5400s)
        # 2. Day 2, Project B, Task B1 (2h = 7200s)
        self.assertEqual(len(data), 2)

        item1 = next(d for d in data if d["project"] == "Project A")
        self.assertEqual(str(item1["date"]), "2025-09-15")
        self.assertEqual(item1["time_entry"], "Task A1")
        self.assertEqual(item1["project_color"], "FF0000")
        self.assertEqual(item1["duration_seconds"], 5400.0)

        item2 = next(d for d in data if d["project"] == "Project B")
        self.assertEqual(str(item2["date"]), "2025-09-16")
        self.assertEqual(item2["duration_seconds"], 7200.0)

    def test_summary_excludes_running_timers(self):
        """
        Verify that live tracks (end_time=Null) are not included in the summary.
        """
        self.client.force_authenticate(user=self.user)
        # Query a range that covers "now"
        start = timezone.now().date().strftime("%Y-%m-%d")
        end = start

        response = self.client.get(self.url, {"start_date": start, "end_date": end})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be empty because the only track today is running
        self.assertEqual(len(response.data), 0)

    def test_summary_date_filtering(self):
        """
        Verify that tracks outside the requested date range are excluded.
        """
        self.client.force_authenticate(user=self.user)
        start = "2025-09-15T00:00:30+05:30"
        end = "2025-09-15T23:59:30+05:30"

        # Query only Day 1 (2025-09-15)
        response = self.client.get(self.url, {"start_date": start, "end_date": end})

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["project"], "Project A")

        start = "2025-09-16T00:00:30+05:30"
        end = "2025-09-16T23:59:30+05:30"

        # Query only Day 2 (2025-09-16)
        response = self.client.get(self.url, {"start_date": start, "end_date": end})

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["project"], "Project B")

    def test_summary_user_isolation(self):
        """
        Verify that a user cannot see another user's summary data.
        """
        self.client.force_authenticate(user=self.user)
        start = "2025-09-15T00:00:30+05:30"
        end = "2025-09-16T23:59:30+05:30"

        # Query range where 'other_user' has data
        response = self.client.get(self.url, {"start_date": start, "end_date": end})

        projects = [d["project"] for d in response.data]
        self.assertNotIn("Other P", projects)

    def test_summary_overnight_task_behavior(self):
        """
        Verify the behavior for tasks that span across midnight.
        Current implementation groups by start_time date.
        """
        self.client.force_authenticate(user=self.user)

        # Create a track starting at 23:00 on Day 3 and ending at 01:00 on Day 4
        day_3 = self.ref_date + timedelta(days=2)
        start_time = day_3.replace(hour=23, minute=0, second=0)
        end_time = start_time + timedelta(hours=2)

        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_a1,
            start_time=start_time,
            end_time=end_time,
        )

        start = "2025-09-17T00:00:00Z"
        end = "2025-09-19T00:00:00Z"

        response = self.client.get(self.url, {"start_date": start, "end_date": end})

        # Expect the 2 hours to be split across the 2 days
        self.assertEqual(len(response.data), 2)

        day1_summary = next(d for d in response.data if d["date"] == "2025-09-17")
        day2_summary = next(d for d in response.data if d["date"] == "2025-09-18")

        self.assertEqual(day1_summary["duration_seconds"], 3600.0)
        self.assertEqual(day2_summary["duration_seconds"], 3600.0)

    def test_summary_multiple_days_task_behavior(self):
        """
        Verify the behavior for tasks that span across multiple days.
        """
        self.client.force_authenticate(user=self.user)

        day_3 = self.ref_date + timedelta(days=2)  # 2025-09-17

        start_time = day_3.replace(hour=20, minute=0, second=0)

        end_time = start_time + timedelta(days=1, hours=6)

        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_a1,
            start_time=start_time,
            end_time=end_time,
        )

        start = "2025-09-17T00:00:00Z"
        end = "2025-09-20T00:00:00Z"

        response = self.client.get(self.url, {"start_date": start, "end_date": end})

        self.assertEqual(len(response.data), 3)

        day1_summary = next(d for d in response.data if d["date"] == "2025-09-17")
        day2_summary = next(d for d in response.data if d["date"] == "2025-09-18")
        day3_summary = next(d for d in response.data if d["date"] == "2025-09-19")

        self.assertEqual(day1_summary["duration_seconds"], 4 * 3600.0)
        self.assertEqual(day2_summary["duration_seconds"], 24 * 3600.0)
        self.assertEqual(day3_summary["duration_seconds"], 2 * 3600.0)

    def test_summary_boundary_filtering(self):
        """
        Verify that tracks overlapping the requested date range are clamped.
        """
        self.client.force_authenticate(user=self.user)

        day_3 = self.ref_date + timedelta(days=2)  # 2025-09-17
        start_time = day_3.replace(hour=22, minute=0, second=0)
        end_time = start_time + timedelta(hours=4)  # 2025-09-18 02:00:00

        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_a1,
            start_time=start_time,
            end_time=end_time,
        )

        # Query only Day 4 (2025-09-18)
        start = "2025-09-18T00:00:00Z"
        end = "2025-09-19T00:00:00Z"

        response = self.client.get(self.url, {"start_date": start, "end_date": end})

        self.assertEqual(len(response.data), 1)

        day2_summary = response.data[0]
        self.assertEqual(day2_summary["date"], "2025-09-18")
        self.assertEqual(day2_summary["duration_seconds"], 2 * 3600.0)

    def test_summary_week_boundaries(self):
        """
        Verify that the endpoint correctly handles the start and end of a week,
        ensuring no boundary bugs exist.
        """
        self.client.force_authenticate(user=self.user)

        # Sunday 2025-10-12 to Saturday 2025-10-18
        start = "2025-10-12T00:00:00Z"
        end = "2025-10-19T00:00:00Z"

        # start boundary
        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_a1,
            start_time=timezone.datetime(2025, 10, 12, 0, 0, 0, tzinfo=dt_timezone.utc),
            end_time=timezone.datetime(2025, 10, 12, 1, 0, 0, tzinfo=dt_timezone.utc),
        )

        # end boundary
        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_a1,
            start_time=timezone.datetime(
                2025, 10, 18, 23, 0, 0, tzinfo=dt_timezone.utc
            ),
            end_time=timezone.datetime(2025, 10, 19, 0, 0, 0, tzinfo=dt_timezone.utc),
        )

        # before the start boundary
        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_a1,
            start_time=timezone.datetime(
                2025, 10, 11, 23, 0, 0, tzinfo=dt_timezone.utc
            ),
            end_time=timezone.datetime(2025, 10, 12, 0, 0, 0, tzinfo=dt_timezone.utc),
        )

        # after the end boundary
        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_a1,
            start_time=timezone.datetime(2025, 10, 19, 0, 0, 0, tzinfo=dt_timezone.utc),
            end_time=timezone.datetime(2025, 10, 19, 1, 0, 0, tzinfo=dt_timezone.utc),
        )

        # overlapping the start boundary
        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_b1,
            start_time=timezone.datetime(
                2025, 10, 11, 23, 30, 0, tzinfo=dt_timezone.utc
            ),
            end_time=timezone.datetime(2025, 10, 12, 0, 30, 0, tzinfo=dt_timezone.utc),
        )

        # overlapping the end boundary
        TimeTrack.objects.create(
            user=self.user,
            time_entry=self.entry_b1,
            start_time=timezone.datetime(
                2025, 10, 18, 23, 30, 0, tzinfo=dt_timezone.utc
            ),
            end_time=timezone.datetime(2025, 10, 19, 0, 30, 0, tzinfo=dt_timezone.utc),
        )

        response = self.client.get(
            self.url, {"start_date": start, "end_date": end, "timezone": "UTC"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        day_start_a = next(
            (
                d
                for d in response.data
                if d["date"] == "2025-10-12" and d["project"] == "Project A"
            ),
            None,
        )
        day_start_b = next(
            (
                d
                for d in response.data
                if d["date"] == "2025-10-12" and d["project"] == "Project B"
            ),
            None,
        )
        day_end_a = next(
            (
                d
                for d in response.data
                if d["date"] == "2025-10-18" and d["project"] == "Project A"
            ),
            None,
        )
        day_end_b = next(
            (
                d
                for d in response.data
                if d["date"] == "2025-10-18" and d["project"] == "Project B"
            ),
            None,
        )

        self.assertIsNotNone(day_start_a)
        self.assertEqual(day_start_a["duration_seconds"], 3600.0)

        self.assertIsNotNone(day_start_b)
        self.assertEqual(day_start_b["duration_seconds"], 1800.0)

        self.assertIsNotNone(day_end_a)
        self.assertEqual(day_end_a["duration_seconds"], 3600.0)

        self.assertIsNotNone(day_end_b)
        self.assertEqual(day_end_b["duration_seconds"], 1800.0)

        # Ensure no other days are included
        dates = {d["date"] for d in response.data}
        self.assertEqual(dates, {"2025-10-12", "2025-10-18"})

    def test_summary_validation_errors(self):
        """
        Verify 400 Bad Request for invalid inputs.
        """
        self.client.force_authenticate(user=self.user)

        # Case 1: Missing parameters
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Case 2: Start date after end date
        response = self.client.get(
            self.url, {"start_date": "2025-09-20", "end_date": "2025-09-10"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.get(
            self.url, {"start_date": "not-a-date", "end_date": "2025-09-10"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
