import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app

client = TestClient(app)

MOCK_USER = {"username": "testuser", "role": "USER"}
MOCK_ADMIN = {"username": "admin", "role": "ADMIN"}

MOCK_PARKING_LOTS = [
    {
        "id": 1,
        "name": "Main Parking",
        "location": "Center",
        "tariff": 5.0,
        "daytariff": 20.0
    }
]

MOCK_SESSIONS = {
    "1": {
        "id": 1,
        "user": "testuser",
        "licenseplate": "ABC123",
        "started": "2024-01-01T10:00:00",
        "stopped": "2024-01-01T12:00:00",
        "duration_minutes": 120,
        "cost": 10.0,
        "parking_lot_id": 1
    }
}

MOCK_ADMIN = {"username": "adminuser", "role": "ADMIN"}

MOCK_PAYMENTS = {
    "transaction": "txn_123",
    "amount": 100.0,
    "initiator": "testuser",
    "created_at": "2024-01-01 12:00:00",
    "completed": "2024-01-01 12:00:00",
    "hash": "hash_123",
    "t_data": {
        "amount": 5.0,
        "date": "2024-01-01",
        "method": "credit_card",
        "issuer": "visa",
        "bank": "test_bank"
    },
    "session_id": "1",
    "parking_lot_id": "1"
}


class TestBillingEndpointUnit:

    def test_get_billing_unauthorized(self):
        response = client.get("/billing/")
        assert response.status_code == 401

    @patch("utils.session_manager.get_session")
    @patch("utils.storage_utils.load_parking_lot_data")
    @patch("utils.storage_utils.load_parking_sessions_data_from_db")
    @patch("utils.storage_utils.load_payment_data_from_db")
    @patch("utils.session_calculator.generate_payment_hash")
    def test_user_billing_success(
        self,
        mock_hash,
        mock_payments,
        mock_sessions,
        mock_lots,
        mock_session
    ):
        mock_session.return_value = MOCK_USER
        mock_lots.return_value = MOCK_PARKING_LOTS
        mock_sessions.return_value = MOCK_SESSIONS
        mock_payments.return_value = MOCK_PAYMENTS
        mock_hash.return_value = "hash_123"

        response = client.get(
            "/billing/",
            headers={"Authorization": "valid-token"}
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        record = data[0]

        assert record["session"]["license_plate"] == "ABC123"
        assert record["amount"] == 10.0
        assert record["payed"] == 5.0
        assert record["balance"] == 5.0
        assert record["thash"] == "hash_123"


    @patch("endpoints.billing_endpoint.get_session")
    @patch("utils.billing_utils.load_parking_lot_data")
    def test_user_billing_no_sessions(self, mock_lots, mock_session):
        mock_session.return_value = MOCK_USER
        mock_lots.return_value = []

        response = client.get(
            "/billing/",
            headers={"Authorization": "valid-token"}
        )

        assert response.status_code == 200
        assert response.json() == []


    @patch("endpoints.billing_endpoint.get_session")
    @patch("utils.billing_utils.load_parking_lot_data")
    @patch("utils.billing_utils.load_parking_sessions_data_from_db")
    @patch("utils.billing_utils.load_payment_data_from_db")
    @patch("utils.billing_utils.generate_payment_hash")
    def test_multiple_payments_same_session(
        self,
        mock_hash,
        mock_payments,
        mock_sessions,
        mock_lots,
        mock_session
    ):
        mock_session.return_value = MOCK_USER
        mock_lots.return_value = MOCK_PARKING_LOTS
        mock_sessions.return_value = MOCK_SESSIONS
        mock_hash.return_value = "hash_multi"
        mock_payments.return_value = [
            {"session_id": "1", "amount": 3.0},
            {"session_id": "1", "amount": 2.0}
        ]

        response = client.get(
            "/billing/",
            headers={"Authorization": "valid-token"}
        )

        record = response.json()[0]
        assert record["payed"] == 5.0
        assert record["balance"] == 5.0

    @patch("endpoints.billing_endpoint.get_session")
    @patch("utils.billing_utils.load_parking_lot_data")
    @patch("utils.billing_utils.load_parking_sessions_data_from_db")
    @patch("utils.billing_utils.load_payment_data_from_db")
    @patch("utils.billing_utils.generate_payment_hash")
    def test_payment_for_other_session_ignored(
        self,
        mock_hash,
        mock_payments,
        mock_sessions,
        mock_lots,
        mock_session
    ):
        mock_session.return_value = MOCK_USER
        mock_lots.return_value = MOCK_PARKING_LOTS
        mock_sessions.return_value = MOCK_SESSIONS
        mock_hash.return_value = "hash_ignore"
        mock_payments.return_value = [
            {"session_id": "999", "amount": 50.0}
        ]

        response = client.get(
            "/billing/",
            headers={"Authorization": "valid-token"}
        )

        record = response.json()[0]
        assert record["payed"] == 0
        assert record["balance"] == 10.0

    @patch("endpoints.billing_endpoint.get_session")
    def test_billing_by_username_forbidden_for_user(self, mock_session):
        mock_session.return_value = MOCK_USER

        response = client.get(
            "/billing/otheruser",
            headers={"Authorization": "valid-token"}
        )

        assert response.status_code == 403

    @patch("endpoints.billing_endpoint.get_session")
    @patch("utils.billing_utils.load_parking_lot_data")
    @patch("utils.billing_utils.load_parking_sessions_data_from_db")
    @patch("utils.billing_utils.load_payment_data_from_db")
    @patch("utils.billing_utils.generate_payment_hash")
    def test_admin_can_view_other_user_billing(
        self,
        mock_hash,
        mock_payments,
        mock_sessions,
        mock_lots,
        mock_session
    ):
        mock_session.return_value = MOCK_ADMIN
        mock_lots.return_value = MOCK_PARKING_LOTS
        mock_sessions.return_value = MOCK_SESSIONS
        mock_payments.return_value = []
        mock_hash.return_value = "hash_admin"

        response = client.get(
            "/billing/testuser",
            headers={"Authorization": "valid-token"}
        )

        assert response.status_code == 200
        assert response.json()[0]["session"]["license_plate"] == "ABC123"
