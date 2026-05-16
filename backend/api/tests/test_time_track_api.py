from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Project, TimeEntry, TimeTrack

User = get_user_model()


class TestTimeTrackAPI(APITestCase):
    """
    Test suite for the TimeTrack API endpoints, covering both list/create
    and detail views.
    """

    def setUp(self):
        """
        Set up initial data and common variables for the tests.
        """
        self.user1 = User.objects.create_user(username="user1", password="password123")
        self.user2 = User.objects.create_user(username="user2", password="password123")

        self.project1 = Project.objects.create(user=self.user1, title="Project Alpha")
        self.time_entry1 = TimeEntry.objects.create(
            project=self.project1, name="Task 1"
        )

        self.track1 = TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.time_entry1,
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1),
        )

        self.running_track1 = TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.time_entry1,
            start_time=timezone.now() - timedelta(minutes=30),
            end_time=None,
        )

        self.project2 = Project.objects.create(user=self.user2, title="Project Beta")
        self.time_entry2 = TimeEntry.objects.create(
            project=self.project2, name="Task 2"
        )
        self.track2 = TimeTrack.objects.create(
            user=self.user2,
            time_entry=self.time_entry2,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() - timedelta(minutes=10),
        )

        self.list_url = reverse("timetrack-list")
        self.detail_url = reverse("timetrack-detail", kwargs={"pk": self.track1.id})
        self.running_track_url = reverse(
            "timetrack-detail", kwargs={"pk": self.running_track1.id}
        )
        self.other_user_track_url = reverse(
            "timetrack-detail", kwargs={"pk": self.track2.id}
        )
        self.live_track_url = reverse("timetrack-live")

        self.base_payload = {
            "time_entry": self.time_entry1.id,
            "start_time": timezone.now().isoformat(),
        }

    def test_start_time_track_success(self):
        """
        Ensure an authenticated user can successfully start a new time track.
        """
        self.client.force_authenticate(user=self.user2)
        payload = self.base_payload.copy()
        payload["time_entry"] = self.time_entry2.id

        response = self.client.post(self.list_url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["time_entry"], self.time_entry2.id)
        self.assertIsNone(response.data["end_time"])

        self.assertTrue(
            TimeTrack.objects.filter(
                user=self.user1, time_entry=self.time_entry1, end_time__isnull=True
            ).exists()
        )

    def test_list_time_tracks_with_date_range_success(self):
        """
        Ensure a user can list their time tracks within a specific date
        range.
        """
        self.client.force_authenticate(user=self.user1)
        now = timezone.now()

        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.time_entry1,
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(days=1, hours=-1),
        )
        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.time_entry1,
            start_time=now - timedelta(days=10),
            end_time=now - timedelta(days=10, hours=-1),
        )
        project2 = Project.objects.create(user=self.user2, title="P2")
        entry2 = TimeEntry.objects.create(project=project2, name="T2")
        TimeTrack.objects.create(
            user=self.user2, time_entry=entry2, start_time=now - timedelta(days=1)
        )

        start_date = now - timedelta(days=5)
        end_date = now

        response = self.client.get(
            self.list_url, {"start_date": start_date, "end_date": end_date}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_list_time_tracks_with_only_start_date_success(self):
        """
        Ensure a user can list their time tracks within a specific date
        range.
        """
        self.client.force_authenticate(user=self.user1)
        now = timezone.now()

        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.time_entry1,
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(days=1, hours=-1),
        )
        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.time_entry1,
            start_time=now - timedelta(days=10),
            end_time=now - timedelta(days=10, hours=-1),
        )
        project2 = Project.objects.create(user=self.user2, title="P2")
        entry2 = TimeEntry.objects.create(project=project2, name="T2")
        TimeTrack.objects.create(
            user=self.user2, time_entry=entry2, start_time=now - timedelta(days=1)
        )

        start_date = (now - timedelta(days=5)).strftime("%Y-%m-%d")
        end_date = ""

        response = self.client.get(
            self.list_url, {"start_date": start_date, "end_date": end_date}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_list_time_tracks_with_only_end_date_success(self):
        """
        Ensure a user can list their time tracks within a specific date
        range.
        """
        self.client.force_authenticate(user=self.user1)
        now = timezone.now()

        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.time_entry1,
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(days=1, hours=-1),
        )
        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.time_entry1,
            start_time=now - timedelta(days=10),
            end_time=now - timedelta(days=10, hours=-1),
        )
        project2 = Project.objects.create(user=self.user2, title="P2")
        entry2 = TimeEntry.objects.create(project=project2, name="T2")
        TimeTrack.objects.create(
            user=self.user2, time_entry=entry2, start_time=now - timedelta(days=3)
        )

        start_date = ""
        end_date = (now - timedelta(days=2)).strftime("%Y-%m-%d")

        response = self.client.get(
            self.list_url, {"start_date": start_date, "end_date": end_date}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_time_tracks_fails_with_invalid_date_format(self):
        """
        Ensure listing tracks fails with 400 for invalid date formats.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            self.list_url,
            {"start_date": "2025-01-01T00:00:00Z", "end_date": "not-a-date"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", response.data)
        self.assertEqual(
            str(response.data["end_date"][0]),
            "Datetime has wrong format. Use one of these formats instead: YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].",
        )

    def test_list_time_tracks_fails_with_start_after_end_date(self):
        """
        Ensure listing tracks fails with 400 if start_date > end_date.
        """
        self.client.force_authenticate(user=self.user1)
        now = timezone.now()
        end_date = now - timedelta(days=1)

        response = self.client.get(
            self.list_url, {"start_date": now, "end_date": end_date}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertEqual(
            response.data["non_field_errors"][0],
            "start_date cannot be after end_date.",
        )

    def test_list_time_tracks_unauthenticated(self):
        """
        Ensure an unauthenticated user cannot list any time tracks.
        """
        now = timezone.now()
        start_date = (now - timedelta(days=5)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        response = self.client.get(
            self.list_url, {"start_date": start_date, "end_date": end_date}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_start_time_track_unauthenticated(self):
        """
        Ensure unauthenticated users receive a 401 Unauthorized error.
        """
        response = self.client.post(self.list_url, self.base_payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(TimeTrack.objects.count(), 3)

    def test_start_time_track_fails_if_already_running(self):
        """
        Ensure a user cannot start a new timer if one is already running,
        enforcing the "Single Running Timer" invariant.
        """
        self.client.force_authenticate(user=self.user1)

        response = self.client.post(self.list_url, self.base_payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertEqual(
            str(response.data["non_field_errors"][0]),
            "You already have a running time track.",
        )

    def test_start_time_track_fails_missing_time_entry_id(self):
        """
        Ensure the request fails if 'time_entry_id' is missing.
        """
        self.client.force_authenticate(user=self.user1)

        # Payload is missing the required 'time_entry_id' field.
        payload = {"start_time": timezone.now().isoformat()}

        initial_track_count = TimeTrack.objects.count()
        response = self.client.post(self.list_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("time_entry", response.data)
        self.assertEqual(str(response.data["time_entry"][0]), "This field is required.")
        self.assertEqual(TimeTrack.objects.count(), initial_track_count)

    def test_start_time_track_fails_for_other_users_time_entry(self):
        """
        Ensure a user cannot create a track for another user's time entry.
        """
        self.client.force_authenticate(user=self.user1)

        payload = self.base_payload.copy()
        payload["time_entry"] = self.time_entry2.id

        response = self.client.post(self.list_url, payload)

        # The serializer validation should fail because the queryset for the
        # time_entry field should be filtered to the current user's entries.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            str(response.data["time_entry"][0]),
            f'Invalid pk "{self.time_entry2.id}" - object does not exist.',
        )

    def test_create_completed_track_fails_end_time_before_start_time(self):
        """
        Ensure creating a completed track fails if end_time is before
        start_time.
        """
        self.client.force_authenticate(user=self.user1)

        now = timezone.now()
        payload = self.base_payload.copy()
        payload.update(
            {
                "start_time": now.isoformat(),
                "end_time": (now - timedelta(minutes=30)).isoformat(),
            }
        )

        initial_track_count = TimeTrack.objects.count()
        response = self.client.post(self.list_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertEqual(
            str(response.data["non_field_errors"][0]),
            "End time must be after start time.",
        )
        self.assertEqual(TimeTrack.objects.count(), initial_track_count)

    def test_list_time_tracks_success(self):
        """
        Ensure an authenticated user can list their own time tracks and
        does not see tracks from other users.
        """
        now = timezone.now()
        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.time_entry1,
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(days=1, hours=-1),
        )
        TimeTrack.objects.create(
            user=self.user1,
            time_entry=self.time_entry1,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2, hours=-2),
        )
        user2_project = Project.objects.create(user=self.user2, title="P2")
        user2_entry = TimeEntry.objects.create(project=user2_project, name="T2")
        user2_track = TimeTrack.objects.create(
            user=self.user2,
            time_entry=user2_entry,
            start_time=now,
            end_time=now + timedelta(hours=1),
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

        response_ids = {item["id"] for item in response.data}
        self.assertNotIn(user2_track.id, response_ids)

    def test_list_time_tracks_unauthenticated(self):
        """
        Ensure an unauthenticated user cannot list any time tracks.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_time_track_success(self):
        """
        Ensure an authenticated user can retrieve their own time track.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.track1.id)
        self.assertEqual(response.data["time_entry"], self.time_entry1.id)

    def test_retrieve_time_track_unauthenticated(self):
        """
        Ensure an unauthenticated user receives a 401 Unauthorized error.
        """
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_other_users_time_track_fails(self):
        """
        Ensure a user gets a 404 Not Found when trying to retrieve another
        user's time track.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.other_user_track_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_non_existent_time_track_fails(self):
        """
        Ensure a 404 is returned for a time track ID that does not exist.
        """
        self.client.force_authenticate(user=self.user1)
        non_existent_url = reverse("timetrack-detail", kwargs={"pk": 9999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_stop_running_time_track_patch_success(self):
        """
        Ensure a user can stop a running timer by PATCHing the end_time.
        """
        self.client.force_authenticate(user=self.user1)
        self.assertIsNone(self.running_track1.end_time)

        end_time = timezone.now()
        payload = {"end_time": end_time.isoformat()}
        response = self.client.patch(self.running_track_url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.running_track1.refresh_from_db()
        self.assertIsNotNone(self.running_track1.end_time)

    def test_update_time_track_put_success(self):
        """
        Ensure a user can fully update a time track using PUT.
        """
        self.client.force_authenticate(user=self.user1)
        now = timezone.now()
        payload = {
            "time_entry": self.time_entry1.id,
            "start_time": (now - timedelta(hours=5)).isoformat(),
            "end_time": (now - timedelta(hours=4)).isoformat(),
        }
        response = self.client.put(self.detail_url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.track1.refresh_from_db()
        self.assertAlmostEqual(
            self.track1.start_time, now - timedelta(hours=5), delta=timedelta(seconds=1)
        )

    def test_update_put_fails_with_partial_data(self):
        """
        Ensure a PUT request fails with 400 if a required field is missing.
        """
        self.client.force_authenticate(user=self.user1)
        payload = {
            # 'time_entry_id' is missing, which should cause an error
            "start_time": (timezone.now() - timedelta(hours=5)).isoformat(),
        }
        response = self.client.put(self.detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("time_entry", response.data)

    def test_update_fails_with_other_users_time_entry(self):
        """
        Ensure a user cannot update their track to point to another user's
        time entry.
        """
        self.client.force_authenticate(user=self.user1)
        payload = {"time_entry": self.time_entry2.id}
        response = self.client.patch(self.detail_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("time_entry", response.data)

    def test_update_time_track_invalid_time_interval(self):
        """
        Ensure updating a track fails if end_time is before start_time.
        """
        self.client.force_authenticate(user=self.user1)
        start_time = self.track1.start_time
        payload = {"end_time": (start_time - timedelta(minutes=10)).isoformat()}
        response = self.client.patch(self.detail_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_delete_time_track_success(self):
        """
        Ensure an authenticated user can delete their own time track.
        """
        self.client.force_authenticate(user=self.user1)
        self.assertTrue(TimeTrack.objects.filter(pk=self.track1.id).exists())
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TimeTrack.objects.filter(pk=self.track1.id).exists())

    def test_delete_time_track_unauthenticated(self):
        """
        Ensure an unauthenticated user cannot delete a time track.
        """
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_other_users_time_track_fails(self):
        """
        Ensure a user gets a 404 when trying to delete another user's track.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(self.other_user_track_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_live_track_success(self):
        """
        Ensure an authenticated user can retrieve their currently running
        time track.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.live_track_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.running_track1.id)
        self.assertIsNone(response.data["end_time"])
        self.assertEqual(response.data["time_entry"], self.time_entry1.id)

    def test_get_live_track_when_none_exists(self):
        """
        Ensure a 204 No Content is returned if the user has no running
        time track.
        """
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(self.live_track_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_live_track_unauthenticated(self):
        """
        Ensure an unauthenticated user receives a 401 Unauthorized error.
        """
        response = self.client.get(self.live_track_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
