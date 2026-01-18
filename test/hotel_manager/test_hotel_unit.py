import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, status

from endpoints.hotel_manager_endpoint import (
    router,
    require_auth,
    require_hotel_manager,
    create_hotel_discount_code,
    get_hotel_discount_codes,
    get_hotel_discount_code_by_code,
    get_managed_parking_lot,
    deactivate_hotel_discount_code,
)
from models.hotel_manager_model import HotelDiscountCodeCreate


class TestRequireAuthDependency:
    """test the require_auth function"""

    def test_require_auth_missing_header(self):
        """test that missing auth header raises 401"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            require_auth(mock_request)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing authorization header" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.get_session")
    def test_require_auth_invalid_token(self, mock_get_session):
        """test that invalid token raises 401"""
        mock_get_session.return_value = None
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "invalid-token"
        with pytest.raises(HTTPException) as exc_info:
            require_auth(mock_request)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired session token" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.get_session")
    def test_require_auth_valid_token(self, mock_get_session):
        """test that valid token returns session user"""
        expected_user = {"id": "test-id", "username": "test_user", "role": "HOTEL_MANAGER"}
        mock_get_session.return_value = expected_user
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "valid-token"
        result = require_auth(mock_request)
        assert result == expected_user


class TestRequireHotelManagerDependency:
    """test the require_hotel_manager dependency function"""

    @patch("endpoints.hotel_manager_endpoint.require_auth")
    def test_require_hotel_manager_wrong_role(self, mock_require_auth):
        """test that non-hotel manager role raises 403"""
        mock_require_auth.return_value = {"id": "user-id", "username": "regular_user", "role": "USER"}
        mock_request = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            require_hotel_manager(mock_request)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Hotel manager privileges required" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.require_auth")
    def test_require_hotel_manager_no_parking_lot(self, mock_require_auth):
        """test that hotel manager without parking lot raises 403"""
        mock_require_auth.return_value = {"id": "mgr-id", "username": "hotel_mgr", "role": "HOTEL_MANAGER"}
        mock_request = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            require_hotel_manager(mock_request)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "No parking lot assigned" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.require_auth")
    def test_require_hotel_manager_valid(self, mock_require_auth):
        """test that valid hotel manager pass"""
        expected_user = {
            "id": "mgr-id",
            "username": "hotel_mgr",
            "role": "HOTEL_MANAGER",
            "managed_parking_lot_id": "1",
        }
        mock_require_auth.return_value = expected_user
        mock_request = MagicMock()
        result = require_hotel_manager(mock_request)
        assert result == expected_user


class TestCreateHotelDiscountCode:
    """test create_hotel_discount_code endpoint"""

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    @patch("endpoints.hotel_manager_endpoint.save_new_discount_to_db")
    def test_create_discount_code_success_dict_format(self, mock_save, mock_get_discount, mock_load_lots):
        """test successful discount code creation with dict format parking lots"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        mock_load_lots.return_value = {"1": {"name": "Test lot"}}
        mock_get_discount.return_value = None
        session_user = {"username": "test_mgr", "managed_parking_lot_id": "1"}
        discount_create = HotelDiscountCodeCreate(
            code="TEST-CODE",
            check_in_date=check_in,
            check_out_date=check_out,
            guest_name="Test Guest",
            notes="VIP",
        )
        response = create_hotel_discount_code(discount_create, session_user)
        assert response["code"] == "TEST-CODE"
        assert response["discount_value"] == 100.0
        assert response["guest_name"] == "Test Guest"
        assert response["created_by"] == "test_mgr"
        mock_save.assert_called_once()

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    @patch("endpoints.hotel_manager_endpoint.save_new_discount_to_db")
    def test_create_discount_code_success_list_format(self, mock_save, mock_get_discount, mock_load_lots):
        """test successful discount code creation with list format parking lots"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        mock_load_lots.return_value = [{"id": "1", "name": "Test Lot"}]
        mock_get_discount.return_value = None
        session_user = {"username": "test_mgr", "managed_parking_lot_id": "1"}
        discount_create = HotelDiscountCodeCreate(
            code="TEST-CODE-2", check_in_date=check_in, check_out_date=check_out
        )
        response = create_hotel_discount_code(discount_create, session_user)
        assert response["code"] == "TEST-CODE-2"
        assert response["discount_value"] == 100.0
        mock_save.assert_called_once()

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    def test_create_discount_code_parking_lot_not_found_dict(self, mock_load_lots):
        """test parking lot not found with dict format"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        mock_load_lots.return_value = {"2": {"name": "Other lot"}}
        session_user = {"username": "test_mgr", "managed_parking_lot_id": "1"}
        discount_create = HotelDiscountCodeCreate(
            code="TEST-CODE", check_in_date=check_in, check_out_date=check_out
        )
        with pytest.raises(HTTPException) as exc_info:
            create_hotel_discount_code(discount_create, session_user)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    def test_create_discount_code_parking_lot_not_found_list(self, mock_load_lots):
        """test parking lot not found with list format"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        mock_load_lots.return_value = [{"id": "2", "name": "Other lot"}]
        session_user = {"username": "test_mgr", "managed_parking_lot_id": "1"}
        discount_create = HotelDiscountCodeCreate(
            code="TEST-CODE", check_in_date=check_in, check_out_date=check_out
        )
        with pytest.raises(HTTPException) as exc_info:
            create_hotel_discount_code(discount_create, session_user)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    def test_create_discount_code_duplicate(self, mock_get_discount, mock_load_lots):
        """test creating duplicate discount code raises 409"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        mock_load_lots.return_value = {"1": {"name": "Test lot"}}
        mock_get_discount.return_value = {"code": "EXISTING-CODE"}
        session_user = {"username": "test_mgr", "managed_parking_lot_id": "1"}
        discount_create = HotelDiscountCodeCreate(
            code="EXISTING-CODE", check_in_date=check_in, check_out_date=check_out
        )
        with pytest.raises(HTTPException) as exc_info:
            create_hotel_discount_code(discount_create, session_user)
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    def test_create_discount_code_past_checkin(self, mock_get_discount, mock_load_lots):
        """test creating code with past checkin date raises 422"""
        check_in = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        mock_load_lots.return_value = {"1": {"name": "Test lot"}}
        mock_get_discount.return_value = None
        session_user = {"username": "test_mgr", "managed_parking_lot_id": "1"}
        discount_create = HotelDiscountCodeCreate(
            code="PAST-CODE", check_in_date=check_in, check_out_date=check_out
        )
        with pytest.raises(HTTPException) as exc_info:
            create_hotel_discount_code(discount_create, session_user)
        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "past" in exc_info.value.detail.lower()

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    @patch("endpoints.hotel_manager_endpoint.save_new_discount_to_db")
    def test_create_discount_code_save_failure(self, mock_save, mock_get_discount, mock_load_lots):
        """test database save failure raises 500"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        mock_load_lots.return_value = {"1": {"name": "Test lot"}}
        mock_get_discount.return_value = None
        mock_save.side_effect = Exception("Database error")
        session_user = {"username": "test_mgr", "managed_parking_lot_id": "1"}
        discount_create = HotelDiscountCodeCreate(
            code="FAIL-CODE", check_in_date=check_in, check_out_date=check_out
        )
        with pytest.raises(HTTPException) as exc_info:
            create_hotel_discount_code(discount_create, session_user)
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to save" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    @patch("endpoints.hotel_manager_endpoint.save_new_discount_to_db")
    def test_create_discount_code_correct_structure(self, mock_save, mock_get_discount, mock_load_lots):
        """test that created discount code has correct structure"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        mock_load_lots.return_value = {"1": {"name": "Test lot"}}
        mock_get_discount.return_value = None
        session_user = {"username": "test_mgr", "managed_parking_lot_id": "1"}
        discount_create = HotelDiscountCodeCreate(
            code="STRUCT-TEST",
            check_in_date=check_in,
            check_out_date=check_out,
            guest_name="Guest Name",
            notes="Test Notes",
        )

        create_hotel_discount_code(discount_create, session_user)
        saved_code = mock_save.call_args[0][0]
        assert saved_code["code"] == "STRUCT-TEST"
        assert saved_code["discount_type"] == "percentage"
        assert saved_code["discount_value"] == 100.0
        assert saved_code["max_uses"] == 1
        assert saved_code["current_uses"] == 0
        assert saved_code["active"]
        assert saved_code["check_in_date"] == check_in
        assert saved_code["check_out_date"] == check_out
        assert saved_code["parking_lot_id"] == "1"
        assert saved_code["created_by"] == "test_mgr"
        assert saved_code["guest_name"] == "Guest Name"
        assert saved_code["notes"] == "Test Notes"
        assert saved_code["is_hotel_code"] == 1
        assert "created_at" in saved_code


class TestGetHotelDiscountCodes:
    """test the get_hotel_discount_codes endpoint"""

    @patch("endpoints.hotel_manager_endpoint.load_discounts_data_from_db")
    def test_get_discount_codes_success(self, mock_load_discounts):
        """test successfully retrieving hotel managers discount codes"""
        mock_load_discounts.return_value = [
            {"code": "CODE-1", "created_by": "test_mgr", "is_hotel_code": True},
            {"code": "CODE-2", "created_by": "other_mgr", "is_hotel_code": True},
            {"code": "CODE-3", "created_by": "test_mgr", "is_hotel_code": True},
            {"code": "ADMIN-CODE", "created_by": "admin", "is_hotel_code": False},
        ]
        session_user = {"username": "test_mgr"}
        response = get_hotel_discount_codes(session_user)
        assert len(response) == 2
        assert all(code["created_by"] == "test_mgr" for code in response)
        assert all(code["is_hotel_code"] for code in response)

    @patch("endpoints.hotel_manager_endpoint.load_discounts_data_from_db")
    def test_get_discount_codes_empty(self, mock_load_discounts):
        """test retrieving when no codes exist"""
        mock_load_discounts.return_value = []
        session_user = {"username": "test_mgr"}
        response = get_hotel_discount_codes(session_user)
        assert response == []

    @patch("endpoints.hotel_manager_endpoint.load_discounts_data_from_db")
    def test_get_discount_codes_none_returned(self, mock_load_discounts):
        """test when load returns none"""
        mock_load_discounts.return_value = None
        session_user = {"username": "test_mgr"}
        response = get_hotel_discount_codes(session_user)
        assert response == []

    @patch("endpoints.hotel_manager_endpoint.load_discounts_data_from_db")
    def test_get_discount_codes_database_error(self, mock_load_discounts):
        """test database error handling"""
        mock_load_discounts.side_effect = Exception("Database error")
        session_user = {"username": "test_mgr"}
        with pytest.raises(HTTPException) as exc_info:
            get_hotel_discount_codes(session_user)
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to load discount codes" in exc_info.value.detail


class TestGetHotelDiscountCodeByCode:
    """test the get_hotel_discount_code_by_code endpoint"""

    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    def test_get_discount_code_success(self, mock_get_discount):
        """test successfully retrieving a specific discount code"""
        mock_get_discount.return_value = {
            "code": "TEST-CODE",
            "created_by": "test_mgr",
            "guest_name": "Test Guest",
            "discount_value": 100.0,
        }
        session_user = {"username": "test_mgr"}
        response = get_hotel_discount_code_by_code("TEST-CODE", session_user)
        assert response["code"] == "TEST-CODE"
        assert response["created_by"] == "test_mgr"

    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    def test_get_discount_code_not_found(self, mock_get_discount):
        """test retrieving non existing code raises 404"""
        mock_get_discount.return_value = None
        session_user = {"username": "test_mgr"}
        with pytest.raises(HTTPException) as exc_info:
            get_hotel_discount_code_by_code("NONEXISTENT", session_user)
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "not found" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    def test_get_discount_code_wrong_owner(self, mock_get_discount):
        """test retrieving code created by a different manager raises 403"""
        mock_get_discount.return_value = {"code": "OTHER-CODE", "created_by": "other_mgr"}
        session_user = {"username": "test_mgr"}
        with pytest.raises(HTTPException) as exc_info:
            get_hotel_discount_code_by_code("OTHER-CODE", session_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "only view discount codes you created" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    def test_get_discount_code_database_error(self, mock_get_discount):
        """test database error handling"""
        mock_get_discount.side_effect = Exception("Database error")
        session_user = {"username": "test_mgr"}
        with pytest.raises(HTTPException) as exc_info:
            get_hotel_discount_code_by_code("TEST-CODE", session_user)
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestDeactivateHotelDiscountCode:
    """test the deactivate_hotel_discount_code endpoint"""

    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    @patch("endpoints.hotel_manager_endpoint.update_existing_discount_in_db")
    def test_deactivate_code_success(self, mock_update, mock_get_discount):
        """test successfully deactivating a discount code"""
        mock_get_discount.return_value = {
            "code": "ACTIVE-CODE",
            "created_by": "test_mgr",
            "active": True,
            "discount_value": 100.0,
        }
        session_user = {"username": "test_mgr"}
        response = deactivate_hotel_discount_code("ACTIVE-CODE", session_user)
        assert response["active"] is False
        assert response["code"] == "ACTIVE-CODE"
        mock_update.assert_called_once()

    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    def test_deactivate_code_not_found(self, mock_get_discount):
        """test deactivating non existent code raises 404"""
        mock_get_discount.return_value = None
        session_user = {"username": "test_mgr"}
        with pytest.raises(HTTPException) as exc_info:
            deactivate_hotel_discount_code("NONEXISTENT", session_user)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    def test_deactivate_code_wrong_owner(self, mock_get_discount):
        """test deactivating code created by different manager raises 403"""
        mock_get_discount.return_value = {"code": "OTHER-CODE", "created_by": "other_mgr", "active": True}
        session_user = {"username": "test_mgr"}
        with pytest.raises(HTTPException) as exc_info:
            deactivate_hotel_discount_code("OTHER-CODE", session_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "only deactivate discount codes you created" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    @patch("endpoints.hotel_manager_endpoint.update_existing_discount_in_db")
    def test_deactivate_code_update_failure(self, mock_update, mock_get_discount):
        """test database update failure raises 500"""
        mock_get_discount.return_value = {"code": "ACTIVE-CODE", "created_by": "test_mgr", "active": True}
        session_user = {"username": "test_mgr"}
        mock_update.side_effect = Exception("Database error")
        with pytest.raises(HTTPException) as exc_info:
            deactivate_hotel_discount_code("ACTIVE-CODE", session_user)
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to deactivate" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.get_discount_by_code")
    @patch("endpoints.hotel_manager_endpoint.update_existing_discount_in_db")
    def test_deactivate_already_inactive_code(self, mock_update, mock_get_discount):
        """test deactivating an already inactive code still works"""
        mock_get_discount.return_value = {"code": "INACTIVE-CODE", "created_by": "test_mgr", "active": False}
        session_user = {"username": "test_mgr"}
        response = deactivate_hotel_discount_code("INACTIVE-CODE", session_user)
        assert response["active"] is False
        mock_update.assert_called_once()


class TestGetManagedParkingLot:
    """test the get_managed_parking_lot endpoint"""

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    def test_get_managed_parking_lot_dict(self, mock_load_lots):
        """test successcully retrieving parking lot in dict format"""
        mock_load_lots.return_value = {"1": {"name": "Test Parking Lot", "capacity": 100, "tariff": 5.0}}
        session_user = {"managed_parking_lot_id": "1"}
        response = get_managed_parking_lot(session_user)
        assert response.status_code == status.HTTP_200_OK
        content = response.body.decode()
        assert "Test Parking Lot" in content
        assert '"id":"1"' in content

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    def test_get_managed_parking_lot_list_format(self, mock_load_lots):
        """test successfully retrieving parking lot in list format"""
        mock_load_lots.return_value = [
            {"id": "1", "name": "Test Parking Lot", "capacity": 100, "tariff": 5.0},
            {"id": "2", "name": "Other Lot", "capacity": 50, "tariff": 4.0},
        ]
        session_user = {"managed_parking_lot_id": "1"}
        response = get_managed_parking_lot(session_user)
        assert response.status_code == status.HTTP_200_OK
        content = response.body.decode()
        assert "Test Parking Lot" in content
        assert "Other Lot" not in content

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    def test_get_managed_parking_lot_found_dict(self, mock_load_lots):
        """test parking lot not found in dict format raises 404"""
        mock_load_lots.return_value = {"2": {"name": "Other Lot"}}
        session_user = {"managed_parking_lot_id": "1"}
        with pytest.raises(HTTPException) as exc_info:
            get_managed_parking_lot(session_user)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    def test_get_managed_parking_lot_not_found_list(self, mock_load_lots):
        """test parking lot not found in list format raises 404"""
        mock_load_lots.return_value = [{"id": "2", "name": "Other Lot"}]
        session_user = {"managed_parking_lot_id": "1"}
        with pytest.raises(HTTPException) as exc_info:
            get_managed_parking_lot(session_user)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @patch("endpoints.hotel_manager_endpoint.load_parking_lot_data")
    def test_get_managed_parking_lot_database_error(self, mock_load_lots):
        """test database error handling"""
        mock_load_lots.side_effect = Exception("Database error")
        session_user = {"managed_parking_lot_id": "1"}
        with pytest.raises(HTTPException) as exc_info:
            get_managed_parking_lot(session_user)
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to load parking lot" in exc_info.value.detail


class TestRouterConfiguration:
    """test router has correct prefix"""

    def test_router_prefix(self):
        """test router has correct prefix"""
        assert router.prefix == "/hotel-manager"

    def test_router_tags(self):
        """test router has correct tags"""
        assert "hotel-manager" in router.tags

    def test_router_responses(self):
        """test router has configured responses"""
        assert 401 in router.responses
        assert 403 in router.responses
        assert 404 in router.responses
