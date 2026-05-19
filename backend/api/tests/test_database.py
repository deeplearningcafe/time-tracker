from datetime import timedelta
from django.test import TestCase
from django.db.utils import IntegrityError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from api.models import Project, TimeEntry, TimeTrack

User = get_user_model()


class TestProjectModel(TestCase):
    """
    Tests for the Project model, including constraints and cascades.
    """

    def setUp(self):
        """Set up two users for testing ownership and constraints."""
        self.user1 = User.objects.create_user(username="user1", password="password123")
        self.user2 = User.objects.create_user(username="user2", password="password123")

    def test_project_creation(self):
        """Test basic creation of a Project."""
        project = Project.objects.create(user=self.user1, title="Work")
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(project.title, "Work")
        self.assertEqual(project.user, self.user1)

    def test_user_cascade_delete(self):
        """Test that deleting a User also deletes their Projects."""
        Project.objects.create(user=self.user1, title="Work")
        self.assertEqual(Project.objects.count(), 1)
        self.user1.delete()
        self.assertEqual(Project.objects.count(), 0)

    def test_unique_project_title_for_user(self):
        """
        Verify a user cannot have two projects with the same title.
        This tests the `unique_together = ('user', 'title')` constraint.
        """
        Project.objects.create(user=self.user1, title="Work")
        with self.assertRaises(IntegrityError):
            Project.objects.create(user=self.user1, title="Work")

    def test_same_project_title_for_different_users(self):
        """
        Verify two different users can have projects with the same title.
        """
        Project.objects.create(user=self.user1, title="Work")
        Project.objects.create(user=self.user2, title="Work")
        self.assertEqual(Project.objects.count(), 2)

    def test_project_can_have_empty_title(self):
        """
        Verify that a project can be created with an empty title string
        as per the business rules.
        """
        project = Project.objects.create(user=self.user1, title="")
        self.assertEqual(project.title, "")
        self.assertEqual(Project.objects.count(), 1)


class TestTimeEntryModel(TestCase):
    """
    Tests for the TimeEntry model, including constraints and cascades.
    """

    def setUp(self):
        """Set up a user and two projects for testing."""
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )
        self.project1 = Project.objects.create(user=self.user, title="Project 1")
        self.project2 = Project.objects.create(user=self.user, title="Project 2")

    def test_time_entry_creation(self):
        """Test basic creation of a TimeEntry."""
        time_entry = TimeEntry.objects.create(project=self.project1, name="Coding")
        self.assertEqual(TimeEntry.objects.count(), 1)
        self.assertEqual(time_entry.name, "Coding")
        self.assertEqual(time_entry.project, self.project1)

    def test_project_cascade_delete(self):
        """Test that deleting a Project also deletes its TimeEntries."""
        TimeEntry.objects.create(project=self.project1, name="Coding")
        self.assertEqual(TimeEntry.objects.count(), 1)
        self.project1.delete()
        self.assertEqual(TimeEntry.objects.count(), 0)

    def test_unique_time_entry_name_for_project(self):
        """
        Verify a project cannot have two time entries with the same name.
        This tests the `unique_together = ('project', 'name')` constraint.
        """
        TimeEntry.objects.create(project=self.project1, name="Coding")
        with self.assertRaises(IntegrityError):
            TimeEntry.objects.create(project=self.project1, name="Coding")

    def test_same_time_entry_name_for_different_projects(self):
        """
        Verify two different projects can have time entries with the same
        name.
        """
        TimeEntry.objects.create(project=self.project1, name="Meeting")
        TimeEntry.objects.create(project=self.project2, name="Meeting")
        self.assertEqual(TimeEntry.objects.count(), 2)

    def test_time_entry_can_have_empty_name(self):
        """
        Verify that a time entry can be created with an empty name string
        as per the business rules.
        """
        time_entry = TimeEntry.objects.create(project=self.project1, name="")
        self.assertEqual(time_entry.name, "")
        self.assertEqual(TimeEntry.objects.count(), 1)


class TestTimeTrackModel(TestCase):
    """
    Tests for the TimeTrack model, including business rules and constraints.
    """

    def setUp(self):
        """Set up users, a project, and a time entry for testing."""
        self.user1 = User.objects.create_user("user1", "user1@test.com", "password123")
        self.user2 = User.objects.create_user("user2", "user2@test.com", "password123")
        project = Project.objects.create(user=self.user1, title="Work")
        self.time_entry = TimeEntry.objects.create(project=project, name="Development")

    def test_time_track_creation(self):
        """Test basic creation of a TimeTrack."""
        start_time = timezone.now()
        track = TimeTrack.objects.create(
            time_entry=self.time_entry,
            user=self.user1,
            start_time=start_time,
            end_time=start_time + timedelta(hours=1),
        )
        self.assertEqual(TimeTrack.objects.count(), 1)
        self.assertEqual(track.user, self.user1)

    def test_time_entry_cascade_delete(self):
        """Test that deleting a TimeEntry deletes its TimeTracks."""
        TimeTrack.objects.create(
            time_entry=self.time_entry, user=self.user1, start_time=timezone.now()
        )
        self.assertEqual(TimeTrack.objects.count(), 1)
        self.time_entry.delete()
        self.assertEqual(TimeTrack.objects.count(), 0)

    def test_unique_running_timer_constraint(self):
        """
        Verify a user can only have one running timer (end_time is NULL).
        This tests the partial unique constraint on the TimeTrack model.
        """
        TimeTrack.objects.create(
            time_entry=self.time_entry,
            user=self.user1,
            start_time=timezone.now(),
            end_time=None,
        )
        with self.assertRaises(IntegrityError):
            TimeTrack.objects.create(
                time_entry=self.time_entry,
                user=self.user1,
                start_time=timezone.now(),
                end_time=None,
            )

    def test_different_users_can_have_running_timers(self):
        """Verify two different users can each have a running timer."""
        TimeTrack.objects.create(
            time_entry=self.time_entry,
            user=self.user1,
            start_time=timezone.now(),
            end_time=None,
        )
        project2 = Project.objects.create(user=self.user2, title="Personal")
        time_entry2 = TimeEntry.objects.create(project=project2, name="Reading")
        TimeTrack.objects.create(
            time_entry=time_entry2,
            user=self.user2,
            start_time=timezone.now(),
            end_time=None,
        )
        self.assertEqual(TimeTrack.objects.filter(end_time__isnull=True).count(), 2)

    def test_end_time_must_be_after_start_time(self):
        """
        Verify that end_time must be chronologically after start_time.
        This test now validates the CheckConstraint on the model.
        """
        start_time = timezone.now()
        with self.assertRaises(IntegrityError):
            TimeTrack.objects.create(
                time_entry=self.time_entry,
                user=self.user1,
                start_time=start_time,
                end_time=start_time - timedelta(minutes=30),
            )

    def test_timetrack_user_must_match_project_user(self):
        """
        Verify that a TimeTrack cannot be assigned to a user who does not
        own the parent project. This tests the model's clean() method.
        """
        track = TimeTrack(
            time_entry=self.time_entry,
            user=self.user2,  # user2 does not own the project
            start_time=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            track.full_clean()  # full_clean() must be called to run clean()

