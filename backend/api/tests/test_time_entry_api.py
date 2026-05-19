from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Project, TimeEntry, TimeTrack

User = get_user_model()


class TestRecentTimeEntriesAPI(APITestCase):
    """
    Test suite for the GET /api/time-entries/recent/ endpoint.
    """

    def setUp(self):
        """
        Set up data for testing the recent time entries endpoint.
        - user1 has recent and old tracks for multiple entries.
        - user2 has some tracks to test data isolation.
        """
        self.user1 = User.objects.create_user(username="user1", password="password123")
        self.user2 = User.objects.create_user(username="user2", password="password123")

        p1 = Project.objects.create(user=self.user1, title="P1")
        now = timezone.now()

        self.entry1_recent = TimeEntry.objects.create(project=p1, name="E1")
        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.entry1_recent,
            start_time=now - timedelta(days=5),
            end_time=now - timedelta(days=5, hours=-1),
        )

        self.entry2_most_recent = TimeEntry.objects.create(project=p1, name="E2")
        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.entry2_most_recent,
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(days=1, hours=-1),
        )

        self.entry3_old = TimeEntry.objects.create(project=p1, name="E3")
        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.entry3_old,
            start_time=now - timedelta(days=35),
            end_time=now - timedelta(days=35, hours=-1),
        )

        p2 = Project.objects.create(user=self.user2, title="P2")
        entry4_user2 = TimeEntry.objects.create(project=p2, name="E4")
        TimeTrack.objects.create(
            user=self.user2,
            time_entry=entry4_user2,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2, hours=-1),
        )

        self.recent_url = reverse("time-entry-recent")

    def test_get_recent_entries_success(self):
        """
        Ensure the endpoint returns unique, recent time entries, ordered
        by the most recently tracked.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.recent_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Verify the order: most recent first
        response_ids = [entry["id"] for entry in response.data]
        expected_ids = [str(self.entry2_most_recent.id), str(self.entry1_recent.id)]
        self.assertEqual(response_ids, expected_ids)

        # Verify that the old entry is not present
        self.assertNotIn(str(self.entry3_old.id), response_ids)

    def test_get_recent_entries_unauthenticated(self):
        """
        Ensure unauthenticated users receive a 401 Unauthorized error.
        """
        response = self.client.get(self.recent_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_recent_entries_no_recent_activity(self):
        """
        Ensure an empty list is returned for a user with no tracks in the
        last 30 days.
        """
        user3 = User.objects.create_user("user3", "pw")
        p3 = Project.objects.create(user=user3, title="P3")
        entry_old_user3 = TimeEntry.objects.create(project=p3, name="Old Entry")
        TimeTrack.objects.create(
            user=user3,
            time_entry=entry_old_user3,
            start_time=timezone.now() - timedelta(days=100),
        )

        self.client.force_authenticate(user=user3)
        response = self.client.get(self.recent_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
