from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Project, TimeEntry, TimeTrack

User = get_user_model()


class TestProjectAPI(APITestCase):
    """
    Test suite for the Project CRUD endpoints and durations.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up two users and projects to test ownership and isolation.
        This data is created once for the entire test class.
        """
        cls.user1 = User.objects.create_user(username="user1", password="password123")
        cls.user2 = User.objects.create_user(username="user2", password="password123")
        cls.project1 = Project.objects.create(user=cls.user1, title="User1 Project")
        cls.project2 = Project.objects.create(user=cls.user2, title="User2 Project")

        cls.list_create_url = reverse("project-list")
        cls.detail_url = reverse("project-detail", kwargs={"pk": cls.project1.id})
        cls.other_user_detail_url = reverse(
            "project-detail", kwargs={"pk": cls.project2.id}
        )
        cls.durations_url = reverse("project-durations")

    def test_list_projects_success(self):
        """
        Ensure an authenticated user can list only their own projects.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_create_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.project1.title)

    def test_list_projects_unauthenticated(self):
        """
        Ensure unauthenticated users cannot list projects.
        """
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_project_success(self):
        """
        Ensure an authenticated user can create a new project.
        """
        self.client.force_authenticate(user=self.user1)
        payload = {"title": "New Test Project"}
        response = self.client.post(self.list_create_url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Project.objects.filter(user=self.user1, title="New Test Project").exists()
        )

    def test_create_project_fails_duplicate_title(self):
        """
        Ensure creating a project with a duplicate title for the same
        user fails, enforcing the unique_together constraint.
        """
        self.client.force_authenticate(user=self.user1)
        payload = {"title": self.project1.title}
        response = self.client.post(self.list_create_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)
        self.assertIn(
            "You already have a project with this title.",
            str(response.data["title"][0]),
        )

    def test_create_project_fails_blank_title(self):
        """
        Ensure creating a project with a blank title fails validation.
        """
        self.client.force_authenticate(user=self.user1)
        payload = {"title": ""}
        response = self.client.post(self.list_create_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)
        self.assertEqual(str(response.data["title"][0]), "This field may not be blank.")

    def test_retrieve_project_success(self):
        """
        Ensure a user can retrieve their own project.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.project1.id))

    def test_retrieve_other_users_project_fails(self):
        """
        Ensure a user gets a 404 Not Found for another user's project.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.other_user_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_project_patch_success(self):
        """
        Ensure a user can partially update their own project with PATCH.
        """
        self.client.force_authenticate(user=self.user1)
        payload = {"title": "Updated Project Title"}
        response = self.client.patch(self.detail_url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project1.refresh_from_db()
        self.assertEqual(self.project1.title, "Updated Project Title")

    def test_update_project_put_fails_with_partial_data(self):
        """
        Ensure a PUT request fails if a required field is missing.
        """
        self.client.force_authenticate(user=self.user1)
        payload = {"title": "This Should Fail"}

        response_put = self.client.put(self.detail_url, payload)
        self.assertEqual(response_put.status_code, status.HTTP_200_OK)
        self.project1.refresh_from_db()
        self.assertEqual(self.project1.title, "This Should Fail")

    def test_update_other_users_project_fails(self):
        """
        Ensure a user cannot update another user's project.
        """
        self.client.force_authenticate(user=self.user1)
        payload = {"title": "Should Not Work"}
        response = self.client.put(self.other_user_detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_project_success(self):
        """
        Ensure a user can delete their own project. Soft delete.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.project1.refresh_from_db()
        self.assertIsNotNone(self.project1.deleted_at)

    def test_delete_other_users_project_fails(self):
        """
        Ensure a user cannot delete another user's project.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(self.other_user_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_project_cascades_related_data(self):
        """
        Ensure deleting a project also deletes its related TimeEntry and
        TimeTrack records.
        """
        project_to_delete = Project.objects.create(
            user=self.user1, title="Project To Delete"
        )
        time_entry = TimeEntry.objects.create(
            project=project_to_delete, name="Cascade Test Entry"
        )
        time_track = TimeTrack.objects.create(
            user=self.user1, time_entry=time_entry, start_time="2025-01-01T12:00:00Z"
        )

        self.assertTrue(TimeEntry.objects.filter(pk=time_entry.id).exists())
        self.assertTrue(TimeTrack.objects.filter(pk=time_track.id).exists())

        self.client.force_authenticate(user=self.user1)
        delete_url = reverse("project-detail", kwargs={"pk": project_to_delete.id})
        response = self.client.delete(delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        project_to_delete.refresh_from_db()
        time_entry.refresh_from_db()
        time_track.refresh_from_db()
        self.assertIsNotNone(project_to_delete.deleted_at)
        self.assertIsNotNone(time_entry.deleted_at)
        self.assertIsNotNone(time_track.deleted_at)

    def test_get_project_durations_success(self):
        """
        Ensure the durations endpoint returns the correct total time per project.
        """
        self.client.force_authenticate(user=self.user1)

        entry1 = TimeEntry.objects.create(project=self.project1, name="Task 1")
        now = timezone.now()

        TimeTrack.objects.create(
            user=self.user1,
            time_entry=entry1,
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
        )

        TimeTrack.objects.create(
            user=self.user1,
            time_entry=entry1,
            start_time=now - timedelta(minutes=30),
            end_time=now,
        )

        # Track 3: Running track (should not be included since end_time is null)
        TimeTrack.objects.create(
            user=self.user1, time_entry=entry1, start_time=now, end_time=None
        )

        # Create a track for user 2 (should not be included)
        entry2 = TimeEntry.objects.create(project=self.project2, name="Task 2")
        TimeTrack.objects.create(
            user=self.user2,
            time_entry=entry2,
            start_time=now - timedelta(hours=1),
            end_time=now,
        )

        response = self.client.get(self.durations_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 1 hour + 30 minutes = 5400 seconds
        self.assertIn(str(self.project1.id), response.data)
        self.assertEqual(response.data[str(self.project1.id)], 5400.0)

        self.assertNotIn(str(self.project2.id), response.data)
