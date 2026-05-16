import json
from io import StringIO
from datetime import timedelta, time

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Project, TimeEntry, TimeTrack

User = get_user_model()


class TestDataAPI(APITestCase):
    """
    Test suite for the Data Summarization (GET /api/summary/) and
    Data Portability (GET /api/data/export/, POST /api/data/import/)
    endpoints.
    """

    def setUp(self):
        """
        Set up initial data for two users to test data isolation,
        summarization, and portability features.
        """
        self.user1 = User.objects.create_user(username="user1", password="password123")
        self.project1_user1 = Project.objects.create(
            user=self.user1, title="Project Alpha"
        )
        self.project2_user1 = Project.objects.create(
            user=self.user1, title="Project Gamma"
        )
        self.entry1_p1 = TimeEntry.objects.create(
            project=self.project1_user1, name="Frontend Work"
        )
        self.entry2_p1 = TimeEntry.objects.create(
            project=self.project1_user1, name="Backend Work"
        )

        # TimeTrack data for user1 within a specific week
        self.today = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)

        one_hour = timedelta(hours=1)
        two_hours = timedelta(hours=2)
        thirty_minutes = timedelta(minutes=30)

        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.entry1_p1,
            start_time=self.today - two_hours,
            end_time=self.today - one_hour,
        )
        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.entry2_p1,
            start_time=self.today - timedelta(days=1) - two_hours,
            end_time=self.today - timedelta(days=1),
        )
        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.entry1_p1,
            start_time=self.today - timedelta(days=3) - thirty_minutes,
            end_time=self.today - timedelta(days=3),
        )

        self.user1_total_seconds = sum(
            delta.total_seconds() for delta in [one_hour, two_hours, thirty_minutes]
        )

        self.user2 = User.objects.create_user(username="user2", password="password123")
        project_user2 = Project.objects.create(user=self.user2, title="Project Beta")
        entry_user2 = TimeEntry.objects.create(project=project_user2, name="Design")
        TimeTrack.objects.create(
            user=self.user2,
            time_entry=entry_user2,
            start_time=self.today - one_hour,
            end_time=self.today,
        )

        # A user with no data to test edge cases
        self.user3_no_data = User.objects.create_user(
            username="user3", password="password123"
        )

        self.summary_url = reverse("summary-list")
        self.export_url = reverse("data-export")
        self.import_url = reverse("data-import-data")

    def test_get_summary_success(self):
        """
        Ensure an authenticated user gets a correct summary of their own
        data for a given date range.
        """
        self.client.force_authenticate(user=self.user1)
        start_date = self.today - timedelta(days=7)
        end_date = self.today

        response = self.client.get(
            self.summary_url, {"start_date": start_date, "end_date": end_date}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

        # Calculate total from response and compare with pre-calculated value
        total_seconds = sum(p.get("duration_seconds", 0) for p in response.data)
        self.assertEqual(total_seconds, self.user1_total_seconds)

        # Ensure user2's project is not in the summary
        project_titles = {p.get("project") for p in response.data}
        self.assertIn("Project Alpha", project_titles)
        self.assertNotIn("Project Beta", project_titles)

    def test_get_summary_unauthenticated(self):
        """
        Ensure an unauthenticated user receives a 401 Unauthorized error.
        """
        start_date = (self.today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = self.today.strftime("%Y-%m-%d")
        response = self.client.get(
            self.summary_url, {"start_date": start_date, "end_date": end_date}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_summary_missing_date_params(self):
        """
        Ensure a 400 Bad Request is returned if date parameters are missing.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.summary_url)  # No params
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_summary_invalid_date_format(self):
        """
        Ensure a 400 Bad Request for invalidly formatted date strings.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            self.summary_url, {"start_date": "2025-13-01", "end_date": "not-a-date"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_summary_no_data_in_range(self):
        """
        Ensure an empty list is returned for a valid range with no data.
        """
        self.client.force_authenticate(user=self.user1)
        # A date range in the future where no tracks exist
        start_date = (self.today + timedelta(days=10)).strftime("%Y-%m-%d")
        end_date = (self.today + timedelta(days=20)).strftime("%Y-%m-%d")

        response = self.client.get(
            self.summary_url, {"start_date": start_date, "end_date": end_date}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_export_data_success(self):
        """
        Ensure an authenticated user can export all their data and it
        doesn't contain other users' data.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.export_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            'attachment; filename="time_tracker_export.json"',
            response["Content-Disposition"],
        )
        data = json.loads(response.content)

        self.assertIn("projects", data)
        self.assertEqual(len(data["projects"]), 2)
        self.assertEqual(len(data["time_entries"]), 2)
        self.assertEqual(len(data["time_tracks"]), 3)

    def test_export_data_for_user_with_no_data(self):
        """
        Ensure a user with no data gets a valid export file with empty lists.
        """
        self.client.force_authenticate(user=self.user3_no_data)
        response = self.client.get(self.export_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)

        self.assertEqual(data["projects"], [])
        self.assertEqual(data["time_entries"], [])
        self.assertEqual(data["time_tracks"], [])

    def test_export_data_unauthenticated(self):
        """
        Ensure an unauthenticated user cannot export data.
        """
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_import_data_success_replaces_old_data(self):
        """
        Ensure importing data successfully deletes all old data for the
        user and creates the new data from the file.
        """
        self.client.force_authenticate(user=self.user1)

        # Define a valid data structure for import
        import_data = {
            "projects": [
                {
                    "title": "New Imported Project",
                    "color": "0000FF",
                    "created_at": "2025-09-10T09:00:00Z",
                }
            ],
            "time_entries": [
                {
                    "project_title": "New Imported Project",
                    "name": "New Task",
                    "created_at": "2025-09-10T09:30:00Z",
                }
            ],
            "time_tracks": [
                {
                    "entry_project_title": "New Imported Project",
                    "entry_name": "New Task",
                    "start_time": "2025-09-10T10:00:00Z",
                    "end_time": "2025-09-10T11:00:00Z",
                }
            ],
        }
        json_file = StringIO(json.dumps(import_data))
        json_file.name = "import.json"

        response = self.client.post(
            self.import_url, {"file": json_file}, format="multipart"
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify old data is gone and new data exists
        self.assertEqual(Project.objects.filter(user=self.user1).count(), 1)
        self.assertTrue(
            Project.objects.filter(
                user=self.user1, title="New Imported Project"
            ).exists()
        )
        # Verify other user's data is untouched
        self.assertTrue(Project.objects.filter(user=self.user2).exists())

    def test_import_data_unauthenticated(self):
        """
        Ensure an unauthenticated user cannot import data.
        """
        json_file = StringIO(json.dumps({"projects": []}))
        json_file.name = "import.json"
        response = self.client.post(
            self.import_url, {"file": json_file}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_import_data_transaction_rolls_back_on_error(self):
        """
        Ensure a file with invalid data (violating integrity) fails and
        the user's original data remains untouched.
        """
        self.client.force_authenticate(user=self.user1)
        # This data is invalid because the time_entry references a project
        # that is not defined in the projects list.
        invalid_data = {
            "projects": [
                {
                    "title": "Valid Project",
                    "color": "00FF00",
                    "created_at": "2025-01-01T10:00:00Z",
                }
            ],
            "time_entries": [
                {
                    "project_title": "Non-Existent Project",
                    "name": "Task",
                    "created_at": "2025-01-01T10:30:00Z",
                }
            ],
        }
        json_file = StringIO(json.dumps(invalid_data))
        json_file.name = "import.json"

        initial_project_count = Project.objects.filter(user=self.user1).count()
        response = self.client.post(
            self.import_url, {"file": json_file}, format="multipart"
        )

        self.assertEqual(
            response.data["error"],
            "Data integrity error: Missing reference 'Non-Existent Project'.",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Verify data was not deleted due to the transaction rollback
        self.assertEqual(
            Project.objects.filter(user=self.user1).count(), initial_project_count
        )

    def test_import_data_missing_file(self):
        """
        Ensure a 400 Bad Request is returned if no file is provided.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.import_url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_import_data_malformed_json(self):
        """
        Ensure a 400 Bad Request is returned for a syntactically invalid
        JSON file.
        """
        self.client.force_authenticate(user=self.user1)
        malformed_json_string = '{"projects": [{"title": "Test"}]'  # Missing }
        json_file = StringIO(malformed_json_string)
        json_file.name = "import.json"

        response = self.client.post(
            self.import_url, {"file": json_file}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
