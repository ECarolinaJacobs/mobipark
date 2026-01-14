import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
import uuid

client = TestClient(app)

MOCK_USER = {"username": "testuser", "role": "USER"}
MOCK_ADMIN = {"username": "adminuser", "role": "ADMIN"}

MOCK_PAYMENT = {
    "transaction": "txn_123",
    "amount": 100.0,
    "initiator": "testuser",
    "session_id": "1",
    "parking_lot_id": "1"
}

MOCK_REFUND = {
    "refund_id": "ref_123",
    "original_transaction_id": "txn_123",
    "amount": 50.0,
    "reason": "Customer request",
    "processed_by": "adminuser",
    "status": "completed"
}

class TestRefundsUnit:
    @patch("endpoints.refunds_endpoint.get_session")
    @patch("endpoints.refunds_endpoint.get_payment_data_by_id")
    @patch("endpoints.refunds_endpoint.get_refunds_by_transaction_id")
    @patch("endpoints.refunds_endpoint.save_new_refund_to_db")
    def test_create_refund_success(self, mock_save, mock_get_refunds, mock_get_payment, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_get_payment.return_value = MOCK_PAYMENT
        mock_get_refunds.return_value = []
        
        refund_data = {
            "original_transaction_id": "txn_123",
            "amount": 50.0,
            "reason": "Test refund"
        }
        
        response = client.post("/refunds", json=refund_data, headers={"Authorization": "admin-token"})
        assert response.status_code == 201
        data = response.json()
        assert data["original_transaction_id"] == "txn_123"
        assert data["amount"] == 50.0
        mock_save.assert_called_once()

    @patch("endpoints.refunds_endpoint.get_session")
    def test_create_refund_user_forbidden(self, mock_session):
        mock_session.return_value = MOCK_USER
        refund_data = {"original_transaction_id": "txn_123", "amount": 50.0, "reason": "test"}
        response = client.post("/refunds", json=refund_data, headers={"Authorization": "user-token"})
        assert response.status_code == 403

    @patch("endpoints.refunds_endpoint.get_session")
    @patch("endpoints.refunds_endpoint.get_payment_data_by_id")
    @patch("endpoints.refunds_endpoint.get_refunds_by_transaction_id")
    def test_create_refund_exceeds_amount(self, mock_get_refunds, mock_get_payment, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_get_payment.return_value = MOCK_PAYMENT
        mock_get_refunds.return_value = [{"amount": 60.0, "status": "completed"}]
        
        refund_data = {
            "original_transaction_id": "txn_123",
            "amount": 50.0, # 100 - 60 = 40 remaining. 50 > 40.
            "reason": "Too much"
        }
        
        response = client.post("/refunds", json=refund_data, headers={"Authorization": "admin-token"})
        assert response.status_code == 422
        assert "exceeds remaining refundable amount" in response.json()["detail"]

    @patch("endpoints.refunds_endpoint.get_session")
    @patch("endpoints.refunds_endpoint.get_refund_by_id")
    def test_get_refund_by_id_admin(self, mock_get_refund, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_get_refund.return_value = MOCK_REFUND
        
        response = client.get("/refunds/ref_123", headers={"Authorization": "admin-token"})
        assert response.status_code == 200
        assert response.json()["refund_id"] == "ref_123"

    @patch("endpoints.refunds_endpoint.get_session")
    @patch("endpoints.refunds_endpoint.get_refund_by_id")
    @patch("endpoints.refunds_endpoint.get_payment_data_by_id")
    def test_get_refund_by_id_owner(self, mock_get_payment, mock_get_refund, mock_session):
        mock_session.return_value = MOCK_USER
        mock_get_refund.return_value = MOCK_REFUND
        mock_get_payment.return_value = MOCK_PAYMENT # initiator is 'testuser'
        
        response = client.get("/refunds/ref_123", headers={"Authorization": "user-token"})
        assert response.status_code == 200
        assert response.json()["refund_id"] == "ref_123"
