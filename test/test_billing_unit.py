import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

client = TestClient(app)

MOCK_USER = {"username": "testuser", "role": "USER"}
MOCK_ADMIN = {"username": "adminuser", "role": "ADMIN"}

MOCK_BILLING_RECORD = [
    {
        "session": {
            "license_plate": "AB-12-CD",
            "started": "2026-01-10T10:00:00",
            "stopped": "2026-01-10T14:30:00",
            "hours": 4.5,
            "days": 0
        },
        "parking": {
            "name": "Central Parking",
            "location": "Downtown",
            "tariff": 3.5,
            "daytariff": 25.0
        },
        "amount": 15.75,
        "thash": "abc123hash",
        "payed": 10.0,
        "balance": 5.75
    }
]


class TestGetBillingUser:
    """Test cases for GET /billing endpoint - retrieve authenticated user's billing information"""

    @patch("endpoints.billing_endpoint.get_session")
    @patch("endpoints.billing_endpoint.billing_utils.get_user_session_by_username")
    @patch("endpoints.billing_endpoint.billing_utils.format_billing_record")
    def test_get_own_billing_success(
        self, mock_format, mock_get_sessions, mock_session
    ):
        """Test cases for GET /billing endpoint - retrieve authenticated user's billing information"""
        mock_session.return_value = MOCK_USER
        mock_get_sessions.return_value = [{}]
        mock_format.return_value = MOCK_BILLING_RECORD

        response = client.get("/billing", headers={"Authorization": "valid-token"})
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert data[0]["session"]["license_plate"] == "AB-12-CD"
        assert data[0]["balance"] == 5.75

        mock_get_sessions.assert_called_once_with("testuser")
        mock_format.assert_called_once()

    @patch("endpoints.billing_endpoint.get_session")
    def test_get_billing_unauthorized(self, mock_session):
        """Test billing retrieval fails without valid authorization token"""
        mock_session.return_value = None

        response = client.get("/billing")
        assert response.status_code == 401
        assert "Unauthorized" in response.text

    @patch("endpoints.billing_endpoint.get_session")
    @patch("endpoints.billing_endpoint.billing_utils.get_user_session_by_username")
    @patch("endpoints.billing_endpoint.billing_utils.format_billing_record")
    def test_get_billing_empty(
        self, mock_format, mock_get_sessions, mock_session
    ):
        """Test successful response when user has no billing records"""

        mock_session.return_value = MOCK_USER
        mock_get_sessions.return_value = []
        mock_format.return_value = []

        response = client.get("/billing", headers={"Authorization": "valid-token"})
        assert response.status_code == 200
        assert response.json() == []


class TestGetBillingAdmin:
    """Test cases for GET /billing/{username} endpoint - admin access to any user's billing information"""

    @patch("endpoints.billing_endpoint.get_session")
    @patch("endpoints.billing_endpoint.billing_utils.get_user_session_by_username")
    @patch("endpoints.billing_endpoint.billing_utils.format_billing_record")
    def test_admin_get_user_billing_success(
        self, mock_format, mock_get_sessions, mock_session
    ):
        """Test successful admin retrieval of another user's billing records"""
        mock_session.return_value = MOCK_ADMIN
        mock_get_sessions.return_value = [{}]
        mock_format.return_value = MOCK_BILLING_RECORD

        response = client.get(
            "/billing/testuser",
            headers={"Authorization": "admin-token"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

        mock_get_sessions.assert_called_once_with("testuser")

    @patch("endpoints.billing_endpoint.get_session")
    def test_admin_billing_missing_token(self, mock_session):
        """Test admin billing endpoint fails without authorization token"""
        mock_session.return_value = None

        response = client.get("/billing/testuser")
        assert response.status_code == 401
        assert "Unauthorized" in response.text

    @patch("endpoints.billing_endpoint.get_session")
    def test_non_admin_cannot_access_other_user(self, mock_session):
        """Test non-admin users cannot access other users' billing information"""
        mock_session.return_value = MOCK_USER

        response = client.get(
            "/billing/otheruser",
            headers={"Authorization": "user-token"}
        )
        assert response.status_code == 403
        assert "admin" in response.text.lower()

    @patch("endpoints.billing_endpoint.get_session")
    @patch("endpoints.billing_endpoint.billing_utils.get_user_session_by_username")
    @patch("endpoints.billing_endpoint.billing_utils.format_billing_record")
    def test_admin_get_nonexistent_user(
        self, mock_format, mock_get_sessions, mock_session
    ):
        """Test admin can query billing for non-existent users (returns empty list)"""

        mock_session.return_value = MOCK_ADMIN
        mock_get_sessions.return_value = []
        mock_format.return_value = []

        response = client.get(
            "/billing/nonexistent_user",
            headers={"Authorization": "admin-token"}
        )
        assert response.status_code == 200
        assert response.json() == []


class TestBillingEdgeCases:
    """Test cases for billing data validation and edge cases"""

    @patch("endpoints.billing_endpoint.get_session")
    @patch("endpoints.billing_endpoint.billing_utils.get_user_session_by_username")
    @patch("endpoints.billing_endpoint.billing_utils.format_billing_record")
    def test_balance_calculation(
        self, mock_format, mock_get_sessions, mock_session
    ):
        """Test billing balance is correctly calculated as amount minus paid"""
        mock_session.return_value = MOCK_USER
        mock_get_sessions.return_value = [{}]
        mock_format.return_value = MOCK_BILLING_RECORD

        response = client.get("/billing", headers={"Authorization": "valid-token"})
        assert response.status_code == 200

        for record in response.json():
            expected_balance = record["amount"] - record["payed"]
            assert abs(record["balance"] - expected_balance) < 0.01

    @patch("endpoints.billing_endpoint.get_session")
    @patch("endpoints.billing_endpoint.billing_utils.get_user_session_by_username")
    @patch("endpoints.billing_endpoint.billing_utils.format_billing_record")
    def test_transaction_hash_exists(
        self, mock_format, mock_get_sessions, mock_session
    ):
        """Test all billing records contain valid transaction hash"""
        mock_session.return_value = MOCK_USER
        mock_get_sessions.return_value = [{}]
        mock_format.return_value = MOCK_BILLING_RECORD

        response = client.get("/billing", headers={"Authorization": "valid-token"})
        assert response.status_code == 200

        for record in response.json():
            assert "thash" in record
            assert isinstance(record["thash"], str)
            assert len(record["thash"]) > 0
