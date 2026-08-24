"""
Auth system tests for the accounts app.

Test matrix:
  1. test_register_success          — POST /register/ → 201 + JWT tokens in response
  2. test_register_duplicate_email  — POST /register/ with same email → 400
  3. test_login_valid_password      — POST /login/ with correct creds → 200 + access token
  4. test_login_invalid_password    — POST /login/ with wrong password → 401
  5. test_me_authenticated          — GET /me/ with valid Bearer token → 200 + user data
  6. test_me_unauthenticated        — GET /me/ without token → 401
  7. test_register_hashes_password  — Confirms the stored password is NOT the plain-text value
  8. test_login_returns_role        — Confirms role field is present in login response
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
ME_URL = "/api/auth/me/"

VALID_PAYLOAD = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "StrongPass123!",
    "role": "customer",
}


class RegistrationTests(APITestCase):
    """Tests for POST /api/auth/register/"""

    def test_register_success_returns_201_and_tokens(self):
        """A new user can register and immediately receives JWT tokens."""
        response = self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()

        # Response must contain both token types
        self.assertIn("tokens", data)
        self.assertIn("access", data["tokens"])
        self.assertIn("refresh", data["tokens"])
        # Token strings must be non-empty
        self.assertTrue(len(data["tokens"]["access"]) > 0)
        self.assertTrue(len(data["tokens"]["refresh"]) > 0)

    def test_register_creates_user_with_correct_role(self):
        """Registered user is persisted with the correct role."""
        self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        user = User.objects.get(username="testuser")
        self.assertEqual(user.role, "customer")

    def test_register_hashes_password_never_stores_plain_text(self):
        """
        Passwords MUST be hashed. The raw password value must not appear
        anywhere in the stored password hash string.
        """
        self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        user = User.objects.get(username="testuser")

        # The stored value should be a hash (e.g., pbkdf2_sha256$...)
        self.assertNotEqual(user.password, VALID_PAYLOAD["password"])
        # Django's check_password must verify the original password correctly
        self.assertTrue(user.check_password(VALID_PAYLOAD["password"]))

    def test_register_duplicate_email_returns_400(self):
        """Registering with an already-used email must fail."""
        self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        duplicate = {**VALID_PAYLOAD, "username": "anotheruser"}
        response = self.client.post(REGISTER_URL, duplicate, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password_returns_400(self):
        """Passwords shorter than 8 characters are rejected."""
        payload = {**VALID_PAYLOAD, "password": "short"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    """Tests for POST /api/auth/login/"""

    def setUp(self):
        """Create a user directly so each login test starts fresh."""
        self.user = User.objects.create_user(
            username="loginuser",
            email="login@example.com",
            password="ValidPass99!",
            role="organiser",
        )

    def test_login_valid_password_returns_200_and_access_token(self):
        """A registered user can log in with the correct password and receive a JWT."""
        payload = {"username": "loginuser", "password": "ValidPass99!"}
        response = self.client.post(LOGIN_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("access", data)
        self.assertTrue(len(data["access"]) > 0)

    def test_login_returns_role_in_response(self):
        """Login response must include the user's role for frontend routing."""
        payload = {"username": "loginuser", "password": "ValidPass99!"}
        response = self.client.post(LOGIN_URL, payload, format="json")

        data = response.json()
        self.assertIn("role", data)
        self.assertEqual(data["role"], "organiser")

    def test_login_invalid_password_returns_401(self):
        """Wrong password must be rejected with 401 Unauthorized."""
        payload = {"username": "loginuser", "password": "WrongPassword!"}
        response = self.client.post(LOGIN_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user_returns_401(self):
        """Attempting to log in as a non-existent user must return 401."""
        payload = {"username": "ghost", "password": "anything"}
        response = self.client.post(LOGIN_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MeViewTests(APITestCase):
    """Tests for GET /api/auth/me/"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="meuser",
            email="me@example.com",
            password="MePass123!",
            role="admin",
        )

    def _get_token(self):
        """Helper: login and return the access token string."""
        response = self.client.post(
            LOGIN_URL,
            {"username": "meuser", "password": "MePass123!"},
            format="json",
        )
        return response.json()["access"]

    def test_me_with_valid_token_returns_200_and_user_data(self):
        """Authenticated users can retrieve their own profile data."""
        token = self._get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["username"], "meuser")
        self.assertEqual(data["email"], "me@example.com")
        self.assertEqual(data["role"], "admin")

    def test_me_without_token_returns_401(self):
        """Unauthenticated requests to /me/ must be rejected."""
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_with_invalid_token_returns_401(self):
        """A tampered or invalid Bearer token must be rejected."""
        self.client.credentials(HTTP_AUTHORIZATION="Bearer this.is.not.valid")
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
