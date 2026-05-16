from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import Project, TimeEntry, TimeTrack

User = get_user_model()


class TestAuthAPI(APITestCase):
    """
    Test suite for the JWT authentication endpoints.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Use setUpTestData for performance. This data is created once per
        class, not per test method.
        """
        cls.username = "testuser"
        cls.password = "testpass123"
        cls.user = User.objects.create_user(
            username=cls.username, password=cls.password
        )
        cls.token_url = reverse("token_obtain_pair")
        cls.refresh_url = reverse("token_refresh")

    def test_obtain_token_success(self):
        """
        Ensure a user can obtain an access and refresh token with valid
        credentials.
        """
        payload = {"username": self.username, "password": self.password}
        response = self.client.post(self.token_url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_obtain_token_invalid_credentials(self):
        """
        Ensure token acquisition fails with invalid credentials.
        """
        payload = {"username": self.username, "password": "wrongpassword"}
        response = self.client.post(self.token_url, payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)

    def test_refresh_token_success(self):
        """
        Ensure a valid refresh token can be used to obtain a new access
        token.
        """
        refresh = RefreshToken.for_user(self.user)
        payload = {"refresh": str(refresh)}
        response = self.client.post(self.refresh_url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_refresh_token_invalid(self):
        """
        Ensure using an invalid or expired refresh token fails.
        """
        payload = {"refresh": "invalidtoken"}
        response = self.client.post(self.refresh_url, payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)
        self.assertIn("token_not_valid", response.data["code"])


class TestUserAPI(APITestCase):
    """
    Test suite for the User creation and retrieval endpoints.
    """

    def setUp(self):
        """
        Set up URLs and a base payload for user tests.
        """
        self.create_user_url = reverse("user-list")
        self.me_url = reverse("user-me")
        self.user_payload = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
        }

    def test_create_user_success(self):
        """
        Ensure a new user can be created successfully.
        """
        response = self.client.post(self.create_user_url, self.user_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, "newuser")

    def test_create_user_fails_duplicate_username(self):
        """
        Ensure creating a user with a duplicate username fails.
        """
        User.objects.create_user(username="newuser", password="password123")
        response = self.client.post(self.create_user_url, self.user_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertEqual(
            str(response.data["username"][0]),
            "A user with that username already exists.",
        )

    def test_create_user_fails_missing_password(self):
        """
        Ensure creating a user with a missing password fails validation.
        """
        payload = self.user_payload.copy()
        del payload["password"]
        response = self.client.post(self.create_user_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertEqual(str(response.data["password"][0]), "This field is required.")

    def test_get_current_user_success(self):
        """
        Ensure an authenticated user can retrieve their own details.
        """
        user = User.objects.create_user(**self.user_payload)
        self.client.force_authenticate(user=user)
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], user.username)
        self.assertEqual(response.data["email"], user.email)

    def test_get_current_user_unauthenticated(self):
        """
        Ensure unauthenticated requests to /users/me/ are rejected.
        """
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
