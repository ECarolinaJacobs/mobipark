import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
from datetime import datetime

client = TestClient(app)

MOCK_USER = {"username": "testuser", "role": "USER"}
MOCK_ADMIN = {"username": "adminuser", "role": "ADMIN"}

MOCK_PAYMENT = {
    "transaction": "txn_123",
    "amount": 100.0,
    "initiator": "testuser",
    "created_at": "2024-01-01 12:00:00",
    "completed": "2024-01-01 12:00:00",
    "hash": "hash_123",
    "t_data": {
        "amount": 100.0,
        "date": "2024-01-01",
        "method": "credit_card",
        "issuer": "visa",
        "bank": "test_bank"
    },
    "session_id": "1",
    "parking_lot_id": "1"
}

class TestPaymentsUnit:
    @patch("endpoints.payments_endpoint.get_session")
    @patch("endpoints.payments_endpoint.save_new_payment_to_db")
    @patch("endpoints.payments_endpoint.generate_transaction_validation_hash")
    @patch("endpoints.payments_endpoint.generate_payment_hash")
    def test_create_payment_success(self, mock_gen_pay_hash, mock_gen_txn_hash, mock_save, mock_session):
        mock_session.return_value = MOCK_USER
        mock_gen_txn_hash.return_value = "new_txn_hash"
        mock_gen_pay_hash.return_value = "new_pay_hash"
        
        payment_data = {
            "amount": 100.0,
            "session_id": 1,
            "parking_lot_id": 1,
            "t_data": {
                "amount": 100.0,
                "date": "2024-01-01",
                "method": "credit_card",
                "issuer": "visa",
                "bank": "test_bank"
            }
        }
        
        response = client.post("/payments", json=payment_data, headers={"Authorization": "valid-token"})
        assert response.status_code == 201
        data = response.json()
        assert data["transaction"] == "new_txn_hash"
        assert data["amount"] == 100.0
        assert data["initiator"] == "testuser"
        mock_save.assert_called_once()

    @patch("endpoints.payments_endpoint.get_session")
    def test_create_payment_negative_amount(self, mock_session):
        mock_session.return_value = MOCK_USER
        payment_data = {
            "amount": -10.0,
            "session_id": 1,
            "parking_lot_id": 1,
            "t_data": {
                "amount": -10.0,
                "date": "2024-01-01",
                "method": "credit_card",
                "issuer": "visa",
                "bank": "test_bank"
            }
        }
        response = client.post("/payments", json=payment_data, headers={"Authorization": "valid-token"})
        assert response.status_code == 422
        # Pydantic structured error
        errors = response.json()["detail"]
        assert any(e["loc"] == ["body", "amount"] for e in errors) or any("negative" in str(e).lower() for e in errors)

    @patch("endpoints.payments_endpoint.get_session")
    @patch("endpoints.payments_endpoint.get_payment_data_by_id")
    def test_get_payment_by_id_owner(self, mock_get_payment, mock_session):
        mock_session.return_value = MOCK_USER
        mock_get_payment.return_value = MOCK_PAYMENT
        
        response = client.get("/payments/txn_123", headers={"Authorization": "valid-token"})
        assert response.status_code == 200
        assert response.json()["transaction"] == "txn_123"

    @patch("endpoints.payments_endpoint.get_session")
    @patch("endpoints.payments_endpoint.get_payment_data_by_id")
    def test_get_payment_by_id_not_owner(self, mock_get_payment, mock_session):
        mock_session.return_value = {"username": "otheruser", "role": "USER"}
        mock_get_payment.return_value = MOCK_PAYMENT
        
        response = client.get("/payments/txn_123", headers={"Authorization": "valid-token"})
        assert response.status_code == 403
        assert "not your own" in response.json()["detail"]

    @patch("endpoints.payments_endpoint.get_session")
    @patch("endpoints.payments_endpoint.get_payment_data_by_id")
    def test_get_payment_by_id_admin(self, mock_get_payment, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_get_payment.return_value = MOCK_PAYMENT
        
        response = client.get("/payments/txn_123", headers={"Authorization": "valid-token"})
        assert response.status_code == 200
        assert response.json()["transaction"] == "txn_123"

    @patch("endpoints.payments_endpoint.get_session")
    @patch("endpoints.payments_endpoint.get_payment_data_by_id")
    @patch("endpoints.payments_endpoint.update_existing_payment_in_db")
    def test_update_payment_admin(self, mock_update, mock_get_payment, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_get_payment.return_value = MOCK_PAYMENT.copy()
        
        update_data = {"amount": 150.0}
        response = client.put("/payments/txn_123", json=update_data, headers={"Authorization": "valid-token"})
        
        assert response.status_code == 200
        assert response.json()["amount"] == 150.0
        mock_update.assert_called_once()

    @patch("endpoints.payments_endpoint.get_session")
    def test_update_payment_user_forbidden(self, mock_session):
        mock_session.return_value = MOCK_USER
        
        update_data = {"amount": 150.0}
        response = client.put("/payments/txn_123", json=update_data, headers={"Authorization": "valid-token"})
        
        assert response.status_code == 403
        assert "permissions" in response.json()["detail"]
