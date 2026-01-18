import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

client = TestClient(app)


MOCK_USER = {
    "id": "123",
    "username": "testuser",
    "password": "hashed_password",
    "hash_type": "bcrypt",
    "name": "Test User",
    "email": "test@example.com",
    "phone": "123456789",
    "role": "USER",
    "created_at": "2024-01-01",
    "birth_year": 1995,
    "active": True,
}

UPDATED_USER = {
    "id": "123",
    "username": "testuser",
    "password": "hashed_password",
    "hash_type": "bcrypt",
    "name": "Updated Name", 
    "email": "test@example.com",
    "phone": "123456789",
    "role": "USER",
    "created_at": "2024-01-01",
    "birth_year": 1995,
    "active": True,
}


# get /profile

class TestGetProfile:
    """
    Test cases for GET /profile endpoint - retrieve user profile information
    """
    @patch("endpoints.profile_endpoint.get_session")
    def test_get_profile_success(self, mock_session):
        """Test successful profile retrieval with valid token"""

        mock_session.return_value = MOCK_USER

        response = client.get(
            "/profile",
            headers={"Authorization": "valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "testuser"
        assert data["name"] == "Test User"
        assert data["role"] == "USER"

        assert "password" not in data
        assert "hash_type" not in data

    @patch("endpoints.profile_endpoint.get_session")
    def test_get_profile_missing_token(self, mock_session):
        """Test profile retrieval fails when authorization token is missing"""
        response = client.get("/profile")

        assert response.status_code == 401
        assert "Missing session token" in response.text

    @patch("endpoints.profile_endpoint.get_session")
    def test_get_profile_invalid_token(self, mock_session):
        """Test profile retrieval fails with invalid authorization token"""
        mock_session.return_value = None

        response = client.get(
            "/profile",
            headers={"Authorization": "invalid-token"}
        )

        assert response.status_code == 401
        assert "Invalid session token" in response.text


# put /profile

class TestUpdateProfile:
    """Test cases for PUT /profile endpoint - update user profile information"""
    @patch("endpoints.profile_endpoint.get_session")
    @patch("endpoints.profile_endpoint.get_user_data_by_username")
    @patch("endpoints.profile_endpoint.update_existing_user_in_db")
    def test_update_profile_name(
        self, mock_update, mock_get_user, mock_session
    ):
        """Test successful profile name update"""

        mock_session.return_value = MOCK_USER.copy()
        mock_get_user.return_value = MOCK_USER.copy()

        response = client.put(
            "/profile",
            json={"name": "Updated Name"},
            headers={"Authorization": "valid-token"}
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Profile updated successfully"
        mock_update.assert_called_once()

    @patch("endpoints.profile_endpoint.get_session")
    @patch("endpoints.profile_endpoint.get_user_data_by_username")
    @patch("endpoints.profile_endpoint.update_existing_user_in_db")
    @patch("endpoints.profile_endpoint.hash_password_bcrypt")
    def test_update_profile_password(
        self, mock_hash, mock_update, mock_get_user, mock_session
    ):
        """Test successful password update with bcrypt hashing"""

        mock_session.return_value = MOCK_USER.copy()
        mock_get_user.return_value = MOCK_USER.copy()
        mock_hash.return_value = "new_hashed_password"

        response = client.put(
            "/profile",
            json={"password": "newpassword123"},
            headers={"Authorization": "valid-token"}
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Profile updated successfully"
        mock_hash.assert_called_once_with("newpassword123")
        mock_update.assert_called_once()

    @patch("endpoints.profile_endpoint.get_session")
    def test_update_profile_missing_token(self, mock_session):
        """Test profile update fails when authorization token is missing"""
        response = client.put(
            "/profile",
            json={"name": "No Token"}
        )

        assert response.status_code == 401
        assert "Missing session token" in response.text

    @patch("endpoints.profile_endpoint.get_session")
    def test_update_profile_invalid_token(self, mock_session):
        """Test profile update fails with invalid authorization token"""

        mock_session.return_value = None

        response = client.put(
            "/profile",
            json={"name": "Invalid Token"},
            headers={"Authorization": "fake-token"}
        )

        assert response.status_code == 401
        assert "Invalid session token" in response.text

    @patch("endpoints.profile_endpoint.get_session")
    @patch("endpoints.profile_endpoint.get_user_data_by_username")
    def test_update_profile_user_not_found(
        self, mock_get_user, mock_session
    ):
        """Test profile update fails when user does not exist in database"""

        mock_session.return_value = MOCK_USER
        mock_get_user.return_value = None

        response = client.put(
            "/profile",
            json={"name": "Updated Name"},
            headers={"Authorization": "valid-token"}
        )

        assert response.status_code == 404
        assert "User not found" in response.text