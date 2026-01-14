import pytest
from datetime import datetime, timedelta
import uuid


class TestAdminCreatesHotelManager:
    """test admin creating hotel manager accounts"""

    def test_admin_can_create_hotel_manager(self, client, admin_token):
        """test admin successfully creates a hotel manager"""
        unique_id = uuid.uuid4().hex[:8]
        username = f"new_hotel_mgr_{unique_id}"
        response = client.post(
            "/auth/register/hotel-manager",
            headers={"Authorization": admin_token},
            json={
                "username": username,
                "name": "New Hotel Manager",
                "password": "securepass123",
                "parking_lot_id": "1",
                "email": "newmgr@hotel.com",
                "phone": "111222333",
            },
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")  # This will show the validation error
        assert response.status_code == 200
        data = response.json()
        assert "Hotel manager" in data["message"]
        assert data["username"] == username
        assert data["managed_parking_lot_id"] == "1"

    def test_admin_create_hotel_manager_invalid_parking_lot(self, client, admin_token):
        """test creating hotel manager with non-existent parking lot should fail"""
        response = client.post(
            "/auth/register/hotel-manager",
            headers={"Authorization": admin_token},
            json={
                "username": "should_fail",
                "name": "Should Fail",
                "password": "password123",
                "parking_lot_id": "99999",
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_non_admin_cannot_create_hotel_manager(self, client, user_token):
        """test regular user cannot create hotel managers"""
        response = client.post(
            "/auth/register/hotel-manager",
            headers={"Authorization": user_token},
            json={
                "username": "should_fail",
                "name": "Should Fail",
                "password": "password123",
                "parking_lot_id": "1",
            },
        )
        assert response.status_code == 403
        assert "Only admins" in response.json()["detail"]

    def test_create_hotel_manager_duplicate_username(self, client, admin_token):
        """test cannot create hotel manager with already existing username"""
        client.post(
            "/auth/register/hotel-manager",
            headers={"Authorization": admin_token},
            json={
                "username": "duplicate_test",
                "name": "First Manager",
                "password": "password123",
                "parking_lot_id": "1",
            },
        )
        response = client.post(
            "/auth/register/hotel-manager",
            headers={"Authorization": admin_token},
            json={
                "username": "duplicate_test",
                "name": "Second Manager",
                "password": "password123",
                "parking_lot_id": "2",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestHotelManagerCreateDiscountCodes:
    """test hotel managers creating discount codes"""

    def test_hotel_manager_creates_discount_code(self, client, hotel_manager_token):
        """test hotel manager can create a 100% discount code"""
        unique_id = uuid.uuid4().hex[:8]
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        response = client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_manager_token},
            json={
                "code": f"GUEST-SMITH-{unique_id}",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "guest_name": "Mr. Smith",
                "notes": "VIP guest room 305",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == f"GUEST-SMITH-{unique_id}"
        assert data["discount_value"] == 100.0
        assert data["discount_type"] == "percentage"
        assert data["parking_lot_id"] == "1"
        assert data["created_by"] == "hotel_mgr_test"
        assert data["is_hotel_code"]
        assert data["guest_name"] == "Mr. Smith"
        assert data["max_uses"] == 1
        assert data["check_in_date"] == check_in
        assert data["check_out_date"] == check_out
        assert data["active"]

    def test_hotel_manager_creates_code_with_minimal_data(self, client, hotel_manager_token):
        """test creating discount code with only required fields"""
        unique_id = uuid.uuid4().hex[:8]
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        response = client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_manager_token},
            json={
                "code": f"MINIMAL-CODE-{unique_id}",
                "check_in_date": check_in,
                "check_out_date": check_out,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == f"MINIMAL-CODE-{unique_id}"
        assert data["discount_value"] == 100.0
        assert data["check_in_date"] == check_in
        assert data["check_out_date"] == check_out

    def test_hotel_manager_cannot_create_code_with_past_checkin(self, client, hotel_manager_token):
        """test hotel manager cannot create code with checkin date in the past"""
        check_in = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        response = client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_manager_token},
            json={
                "code": "PAST-CHECKIN",
                "check_in_date": check_in,
                "check_out_date": check_out,
            },
        )
        assert response.status_code == 422
        assert "past" in response.json()["detail"].lower()

    def test_hotel_manager_cannot_create_code_with_invalid_dates(self, client, hotel_manager_token):
        """test hotel manager cannot create code with checkout before checkin"""
        check_in = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_manager_token},
            json={
                "code": "INVALID-DATES",
                "check_in_date": check_in,
                "check_out_date": check_out,
            },
        )
        assert response.status_code == 422
        assert "after" in response.json()["detail"].lower()

    def test_hotel_manager_cannot_create_duplicate_code(self, client, hotel_manager_token):
        """test hotel manager cannot create duplicate discount codes"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_manager_token},
            json={"code": "DUPLICATE-TEST", "check_in_date": check_in, "check_out_date": check_out},
        )
        response = client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_manager_token},
            json={"code": "DUPLICATE-TEST", "check_in_date": check_in, "check_out_date": check_out},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_regular_user_cannot_create_hotel_discount_codes(self, client, user_token):
        """test regular user cannot create hotel discount codes"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        response = client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": user_token},
            json={"code": "SHOULD-FAIL", "check_in_date": check_in, "check_out_date": check_out},
        )

        assert response.status_code == 403
        assert "Hotel manager privileges required" in response.json()["detail"]

    def test_unauthenticated_cannot_create_discount_codes(self, client):
        """test unauthenticated user cannot create discount codes"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        response = client.post(
            "/hotel-manager/discount-codes",
            json={"code": "SHOULD-FAIL", "check_in_date": check_in, "check_out_date": check_out},
        )
        assert response.status_code == 401


class TestHotelManagerViewDiscountCodes:
    """test hotel managers viewing their discount codes"""

    def test_hotel_manager_views_all_their_codes(self, client, hotel_manager_token):
        """test hotel manager can view all their discount codes"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_manager_token},
            json={"code": "CODE-1", "check_in_date": check_in, "check_out_date": check_out},
        )

        client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_manager_token},
            json={"code": "CODE-2", "check_in_date": check_in, "check_out_date": check_out},
        )

        response = client.get("/hotel-manager/discount-codes", headers={"Authorization": hotel_manager_token})

        codes = response.json()
        assert len(codes) >= 3

    def test_hotel_manager_views_specific_code(self, client, hotel_manager_token):
        """test hotel manager can view a specific discount code"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        response = client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_manager_token},
            json={
                "code": "SPECIFIC-CODE",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "guest_name": "Jane Doe",
                "notes": "Premium suite",
            },
        )
        response = client.get(
            "/hotel-manager/discount-codes/SPECIFIC-CODE", headers={"Authorization": hotel_manager_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "SPECIFIC-CODE"
        assert data["guest_name"] == "Jane Doe"
        assert data["notes"] == "Premium suite"
        assert data["check_in_date"] == check_in
        assert data["check_out_date"] == check_out

    def test_hotel_manager_cannot_view_nonexistent_code(self, client, hotel_manager_token):
        """test viewing non-existent code returns 404"""
        response = client.get(
            "/hotel-manager/discount-codes/DOES-NOT-EXIST", headers={"Authorization": hotel_manager_token}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_regular_user_cannot_view_hotel_codes(self, client, user_token):
        """test regular user cannot view hotel discount codes"""
        response = client.get("/hotel-manager/discount-codes", headers={"Authorization": user_token})
        assert response.status_code == 403


class TestHotelManagerDeactivateDiscountCodes:
    """test hotel managers deactivating discount codes"""

    def test_hotel_manager_deactivates_code(self, client, hotel_manager_token):
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_manager_token},
            json={"code": "DEACTIVATE-ME", "check_in_date": check_in, "check_out_date": check_out},
        )
        response = client.delete(
            "/hotel-manager/discount-codes/DEACTIVATE-ME", headers={"Authorization": hotel_manager_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert not data["active"]
        assert data["code"] == "DEACTIVATE-ME"
        get_response = client.get(
            "/hotel-manager/discount-codes/DEACTIVATE-ME", headers={"Authorization": hotel_manager_token}
        )
        assert not get_response.json()["active"]

    def test_hotel_manager_cannot_deactivate_nonexistent_code(self, client, hotel_manager_token):
        """test deactivating non-existent code should return 404"""
        response = client.delete(
            "/hotel-manager/discount-codes/DOES-NOT-EXIST", headers={"Authorization": hotel_manager_token}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_regular_user_cannot_deactivate_codes(self, client, user_token):
        """test regular user cannot deactivate hotel codes"""
        response = client.delete(
            "/hotel-manager/discount-codes/EXISTING-CODE", headers={"Authorization": user_token}
        )
        assert response.status_code == 403


class TestHotelManagerViewParkingLot:
    """test hotel managers can view their assigned parking lot"""

    def test_hotel_manager_views_managed_parking_lot(self, client, hotel_manager_token):
        """test hotel manager can view their assigned parking lot"""
        from utils import storage_utils

        print(f"DB_PATH in test: {storage_utils.DB_PATH}")

        response = client.get(
            "/hotel-manager/managed-parking-lot", headers={"Authorization": hotel_manager_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "1"
        assert data["name"] == "Hotel Royal Parking"
        assert "capacity" in data
        assert "tariff" in data

    def test_regular_user_cannot_view_managed_parking_lot(self, client, user_token):
        """test regular user cannot access managed parking lot endpoint"""
        response = client.get("/hotel-manager/managed-parking-lot", headers={"Authorization": user_token})
        assert response.status_code == 403


class TestCompleteHotelManagerWorkflow:
    """test the complete hotel manager workflow end to end"""

    def test_complete_workflow(self, client, admin_token):
        """test complete workflow from hotel manager creation to discount code usage"""
        # admin creates hotel manager
        unique_id = uuid.uuid4().hex[:8]
        username = f"workflow_test_mgr_{unique_id}"
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        response = client.post(
            "/auth/register/hotel-manager",
            headers={"Authorization": admin_token},
            json={
                "username": username,
                "name": "Workflow Test Manager",
                "password": "admin123",
                "parking_lot_id": "2",
                "email": "workflow@test.com",
            },
        )
        assert response.status_code == 200
        assert response.json()["managed_parking_lot_id"] == "2"
        # hotel manager logs in
        response = client.post("/auth/login", json={"username": username, "password": "admin123"})
        assert response.status_code == 200
        hotel_token = response.json()["session_token"]

        # hotel manager views their assigned parking lot
        response = client.get("/hotel-manager/managed-parking-lot", headers={"Authorization": hotel_token})
        assert response.status_code == 200
        assert response.json()["id"] == "2"
        assert response.json()["name"] == "Downtown Parking"

        # hotel manager creates discount code for guest
        response = client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_token},
            json={
                "code": "WORKFLOW-GUEST-001",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "guest_name": "Workflow Guest",
                "notes": "Conference attendee",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "WORKFLOW-GUEST-001"
        assert data["discount_value"] == 100.0
        assert data["parking_lot_id"] == "2"
        assert data["check_in_date"] == check_in
        assert data["check_out_date"] == check_out

        # hotel manager views all of their codes
        response = client.get("/hotel-manager/discount-codes", headers={"Authorization": hotel_token})
        assert response.status_code == 200
        codes = response.json()
        assert any(c["code"] == "WORKFLOW-GUEST-001" for c in codes)
        # hotel manager creates another code
        response = client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": hotel_token},
            json={"code": "WORKFLOW-GUEST-002", "check_in_date": check_in, "check_out_date": check_out},
        )
        assert response.status_code == 201
        # hotel manager views specific code
        response = client.get(
            "/hotel-manager/discount-codes/WORKFLOW-GUEST-001", headers={"Authorization": hotel_token}
        )
        assert response.status_code == 200
        assert response.json()["guest_name"] == "Workflow Guest"

        # guest checks out, hotel manager deactivates code
        response = client.delete(
            "/hotel-manager/discount-codes/WORKFLOW-GUEST-001", headers={"Authorization": hotel_token}
        )
        assert response.status_code == 200
        assert not response.json()["active"]

        # verify code is deactivated
        response = client.get("/hotel-manager/discount-codes", headers={"Authorization": hotel_token})
        codes = response.json()
        deactivated_code = next(c for c in codes if c["code"] == "WORKFLOW-GUEST-001")
        assert not deactivated_code["active"]


class TestHotelManagerIsolation:
    """test that hotel managers can only manage their own codes and parking lot"""

    def test_hotel_managers_cannot_see_each_others_codes(self, client, admin_token):
        """test hotel managers are isolated from other hotel managers"""
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        client.post(
            "/auth/register/hotel-manager",
            headers={"Authorization": admin_token},
            json={
                "username": "hotel_mgr_1",
                "name": "Manager 1",
                "password": "admin123",
                "parking_lot_id": "1",
            },
        )
        client.post(
            "/auth/register/hotel-manager",
            headers={"Authorization": admin_token},
            json={
                "username": "hotel_mgr_2",
                "name": "Manager 2",
                "password": "admin123",
                "parking_lot_id": "2",
            },
        )
        # login as manager 1
        response = client.post("/auth/login", json={"username": "hotel_mgr_1", "password": "admin123"})
        token_1 = response.json()["session_token"]
        # login as manager 2
        response = client.post("/auth/login", json={"username": "hotel_mgr_2", "password": "admin123"})
        token_2 = response.json()["session_token"]

        # manager 1 and 2 create a code
        client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": token_1},
            json={"code": "MGR1-CODE", "check_in_date": check_in, "check_out_date": check_out},
        )
        client.post(
            "/hotel-manager/discount-codes",
            headers={"Authorization": token_2},
            json={"code": "MGR2-CODE", "check_in_date": check_in, "check_out_date": check_out},
        )
        # manager 1 should only see their own code
        response = client.get("/hotel-manager/discount-codes", headers={"Authorization": token_1})
        codes_1 = response.json()
        assert all(c["created_by"] == "hotel_mgr_1" for c in codes_1)
        assert any(c["code"] == "MGR1-CODE" for c in codes_1)
        assert not any(c["code"] == "MGR2-CODE" for c in codes_1)
        # manager 2 should only see their own code
        response = client.get("/hotel-manager/discount-codes", headers={"Authorization": token_2})
        codes_2 = response.json()
        assert all(c["created_by"] == "hotel_mgr_2" for c in codes_2)
        assert any(c["code"] == "MGR2-CODE" for c in codes_2)
        assert not any(c["code"] == "MGR1-CODE" for c in codes_2)

        # manager 2 cannot view manager 1s code
        response = client.get("/hotel-manager/discount-codes/MGR1-CODE", headers={"Authorization": token_2})
        assert response.status_code == 403
        # manager 2 cannot deactivate manager 1s code
        response = client.delete(
            "/hotel-manager/discount-codes/MGR1-CODE", headers={"Authorization": token_2}
        )
        assert response.status_code == 403
