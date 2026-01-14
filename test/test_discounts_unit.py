import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
from datetime import datetime, timedelta

client = TestClient(app)

MOCK_ADMIN = {"username": "adminuser", "role": "ADMIN"}

MOCK_DISCOUNT = {
    "code": "SAVE10",
    "discount_type": "percentage",
    "discount_value": 10.0,
    "max_uses": 100,
    "current_uses": 0,
    "active": True,
    "created_at": "2024-01-01 12:00:00"
}

class TestDiscountsUnit:
    @patch("endpoints.refunds_endpoint.get_session")
    @patch("endpoints.refunds_endpoint.get_discount_by_code")
    @patch("endpoints.refunds_endpoint.save_new_discount_to_db")
    def test_create_discount_code_success(self, mock_save, mock_get_discount, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_get_discount.return_value = None
        
        discount_data = {
            "code": "NEWCODE",
            "discount_type": "fixed",
            "discount_value": 5.0,
            "max_uses": 50
        }
        
        response = client.post("/discount-codes", json=discount_data, headers={"Authorization": "admin-token"})
        assert response.status_code == 201
        assert response.json()["code"] == "NEWCODE"
        mock_save.assert_called_once()

    @patch("endpoints.refunds_endpoint.get_session")
    @patch("endpoints.refunds_endpoint.get_discount_by_code")
    def test_create_discount_code_duplicate(self, mock_get_discount, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_get_discount.return_value = MOCK_DISCOUNT
        
        discount_data = {
            "code": "SAVE10",
            "discount_type": "percentage",
            "discount_value": 10.0
        }
        
        response = client.post("/discount-codes", json=discount_data, headers={"Authorization": "admin-token"})
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @patch("endpoints.refunds_endpoint.get_session")
    @patch("endpoints.refunds_endpoint.get_discount_by_code")
    @patch("endpoints.refunds_endpoint.update_existing_discount_in_db")
    def test_update_discount_code(self, mock_update, mock_get_discount, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_get_discount.return_value = MOCK_DISCOUNT.copy()
        
        update_data = {
            "code": "SAVE10",
            "discount_type": "percentage",
            "discount_value": 15.0
        }
        
        response = client.put("/discount-codes/SAVE10", json=update_data, headers={"Authorization": "admin-token"})
        assert response.status_code == 200
        assert response.json()["discount_value"] == 15.0
        mock_update.assert_called_once()

    @patch("endpoints.refunds_endpoint.get_session")
    @patch("endpoints.refunds_endpoint.get_discount_by_code")
    @patch("endpoints.refunds_endpoint.update_existing_discount_in_db")
    def test_deactivate_discount_code(self, mock_update, mock_get_discount, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_get_discount.return_value = MOCK_DISCOUNT.copy()
        
        response = client.delete("/discount-codes/SAVE10", headers={"Authorization": "admin-token"})
        assert response.status_code == 200
        assert response.json()["active"] is False
        mock_update.assert_called_once()
