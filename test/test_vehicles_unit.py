import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import uuid
from main import app
from endpoints.vehicles_endpoint import normalize_plate


client = TestClient(app)

MOCK_USER = {"username": "testuser", "role": "USER"}

MOCK_ADMIN = {"username": "testuser", "role": "ADMIN"}

MOCK_VEHICLE = {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "testuser",
    "license_plate": "AB-12-CD",
    "make": "Toyota",
    "model": "Camry",
    "color": "Silver",
    "year": 2023,
    "created_at": "2024-01-01T00:00:00",
}

MOCK_VEHICLE_2 = {
    "id": "223e4567-e89b-12d3-a456-426614174001",
    "user_id": "otheruser",
    "license_plate": "XY-99-ZZ",
    "make": "Honda",
    "model": "Civic",
    "color": "Blue",
    "year": 2022,
    "created_at": "2024-01-01T00:00:00",
}


class TestCreateVehicle:
    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.load_vehicle_data_from_db")
    @patch("endpoints.vehicles_endpoint.save_new_vehicle_to_db")
    @patch("uuid.uuid4")
    def test_create_vehicle_success(self, mock_uuid, mock_save, mock_load, mock_session):
        mock_session.return_value = MOCK_USER
        mock_load.return_value = []
        mock_uuid.return_value = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
        vehicle_data = {
            "user_id": "testuser",
            "license_plate": "AB-12-CD",
            "make": "Toyota",
            "model": "Camry",
            "color": "Silver",
            "year": 2023,
        }
        response = client.post("/vehicles", json=vehicle_data, headers={"Authorization": "valid-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["license_plate"] == "AB-12-CD"
        assert data["make"] == "Toyota"
        assert data["user_id"] == "testuser"
        assert "created_at" in data
        mock_save.assert_called_once()

    @patch("endpoints.vehicles_endpoint.get_session")
    def test_create_vehicle_unauthorized(self, mock_session):
        mock_session.return_value = None
        vehicle_data = {
            "user_id": "testuser",
            "license_plate": "AB-12-CD",
            "make": "Toyota",
            "model": "Camry",
            "color": "Silver",
            "year": 2023,
        }
        response = client.post("/vehicles", json=vehicle_data)
        assert response.status_code == 401
        assert "Unauthorized" in response.text

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.load_vehicle_data_from_db")
    def test_create_vehicle_duplicate(self, mock_load, mock_session):
        mock_session.return_value = MOCK_USER
        mock_load.return_value = [MOCK_VEHICLE]
        vehicle_data = {
            "user_id": "testuser",
            "license_plate": "AB-12-CD",
            "make": "Toyota",
            "model": "Camry",
            "color": "Silver",
            "year": 2023,
        }
        response = client.post("/vehicles", json=vehicle_data, headers={"Authorization": "valid-token"})
        assert response.status_code == 400
        assert "Vehicle already exists" in response.text

    def test_create_vehicle_invalid_plate_format(self):
        vehicle_data = {
            "user_id": "testuser",
            "license_plate": "INVALID",
            "make": "Toyota",
            "model": "Camry",
            "color": "Silver",
            "year": 2023,
        }
        response = client.post("/vehicles", json=vehicle_data, headers={"Authorization": "valid-token"})
        assert response.status_code == 422

    def test_create_vehicle_missing_required_field(self):
        vehicle_data = {
            "user_id": "testuser",
            "make": "Toyota",
            "color": "Silver",
            "year": 2023,
        }
        response = client.post("/vehicles", json=vehicle_data, headers={"Authorization": "valid-token"})
        assert response.status_code == 422


class TestGetVehicles:
    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.get_vehicle_data_by_user")
    def test_get_own_vehicles(self, mock_get_vehicles, mock_session):
        mock_session.return_value = MOCK_USER
        mock_get_vehicles.return_value = [MOCK_VEHICLE]
        response = client.get("/vehicles", headers={"Authorization": "valid-token"})
        assert response.status_code == 200
        data = response.json()
        assert "vehicles" in data
        assert len(data["vehicles"]) == 1
        assert data["vehicles"][0]["license_plate"] == "AB-12-CD"
        mock_get_vehicles.assert_called_once_with("testuser")

    @patch("endpoints.vehicles_endpoint.get_session")
    def test_get_vehicles_unauthoried(self, mock_session):
        mock_session.return_value = None
        response = client.get("/vehicles")
        assert response.status_code == 401
        assert "Unauthorized" in response.text

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.get_vehicle_data_by_user")
    def test_admin_get_other_user_vehicles(self, mock_get_vehicles, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_get_vehicles.return_value = [MOCK_VEHICLE]
        response = client.get("/vehicles/testuser", headers={"Authorization": "admin-token"})
        assert response.status_code == 200
        data = response.json()
        assert "vehicles" in data
        mock_get_vehicles.assert_called_once_with("testuser")

    @patch("endpoints.vehicles_endpoint.get_session")
    def test_non_admin_cannot_get_other_user_vehicles(self, mock_session):
        mock_session.return_value = MOCK_USER
        response = client.get("/vehicles/otheruser", headers={"Authorization": "user-token"})
        assert response.status_code == 403
        assert "Access denied" in response.text


class TestUpdateVehicle:
    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.find_vehicle_by_license_plate")
    @patch("endpoints.vehicles_endpoint.update_existing_vehicle_in_db")
    def test_update_own_vehicle(self, mock_update, mock_find, mock_session):
        mock_session.return_value = MOCK_USER
        mock_find.return_value = MOCK_VEHICLE.copy()
        update_data = {
            "user_id": "testuser",
            "license_plate": "AB-12-CD",
            "make": "Toyota",
            "model": "Camry",
            "color": "Red",
            "year": 2023,
        }
        response = client.put("/vehicles/AB12CD", json=update_data, headers={"Authorization": "valid-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["color"] == "Red"
        mock_update.assert_called_once()

    @patch("endpoints.vehicles_endpoint.get_session")
    def test_update_vehicle_unauthorized(self, mock_session):
        mock_session.return_value = None
        update_data = {
            "user_id": "testuser",
            "license_plate": "AB-12-CD",
            "make": "Toyota",
            "model": "Camry",
            "color": "Red",
            "year": 2023,
        }
        response = client.put("/vehicles/AB12CD", json=update_data)
        assert response.status_code == 401
        assert "Unauthorized" in response.text

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.find_vehicle_by_license_plate")
    def test_update_other_user_vehicle_forbidden(self, mock_find, mock_session):
        mock_session.return_value = MOCK_USER
        mock_find.return_value = MOCK_VEHICLE_2.copy()
        update_data = {
            "user_id": "otheruser",
            "license_plate": "XY-99-ZZ",
            "make": "Honda",
            "model": "Civic",
            "color": "Red",
            "year": 2022,
        }
        response = client.put("/vehicles/AB12CD", json=update_data)
        assert response.status_code == 401
        assert "Unauthorized" in response.text
        response = client.put("/vehicles/XY99ZZ", json=update_data, headers={"Authorization": "user-token"})
        assert response.status_code == 403
        assert "Forbidden" in response.text

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.find_vehicle_by_license_plate")
    @patch("endpoints.vehicles_endpoint.update_existing_vehicle_in_db")
    def test_admin_update_other_user_vehicle(self, mock_update, mock_find, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_find.return_value = MOCK_VEHICLE.copy()
        update_data = {
            "user_id": "testuser",
            "license_plate": "AB-12-CD",
            "make": "Toyota",
            "model": "Camry",
            "color": "Red",
            "year": 2023,
        }
        response = client.put("/vehicles/AB12CDE", json=update_data, headers={"Authorization": "admin-token"})
        assert response.status_code == 200
        mock_update.assert_called_once()

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.load_vehicle_data_from_db")
    def test_update_nonexistent_vehicle(self, mock_load, mock_session):
        mock_session.return_value = MOCK_USER
        mock_load.return_value = []
        update_data = {
            "user_id": "testuser",
            "license_plate": "AB-12-CD",
            "make": "Toyota",
            "model": "Camry",
            "color": "Red",
            "year": 2023,
        }
        response = client.put("/vehicles/ZZ99ZZ", json=update_data, headers={"Authorization": "admin-token"})
        assert response.status_code == 404
        assert "Vehicle not found" in response.text


class TestDeleteVehicle:
    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.find_vehicle_by_license_plate")
    @patch("endpoints.vehicles_endpoint.delete_vehicle_from_db")
    def test_delete_own_vehicle(self, mock_delete, mock_find, mock_session):
        mock_session.return_value = MOCK_USER
        mock_find.return_value = MOCK_VEHICLE.copy()
        mock_delete.return_value = True
        response = client.delete("/vehicles/AB12CD", headers={"Authorization": "valid-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Deleted"
        mock_delete.assert_called_once()

    @patch("endpoints.vehicles_endpoint.get_session")
    def test_delete_vehicle_unauthorized(self, mock_session):
        mock_session.return_value = None
        response = client.delete("/vehicles/AB12CD")
        assert response.status_code == 401
        assert "Unauthorized" in response.text

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.find_vehicle_by_license_plate")
    def test_delete_other_user_vehicle_forbidden(self, mock_find, mock_session):
        mock_session.return_value = MOCK_USER
        mock_find.return_value = MOCK_VEHICLE_2.copy()
        response = client.delete("/vehicles/XY99ZZ", headers={"Authorization": "user-token"})
        assert response.status_code == 403
        assert "Forbidden" in response.text

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.find_vehicle_by_license_plate")
    @patch("endpoints.vehicles_endpoint.delete_vehicle_from_db")
    def test_admin_delete_other_user_vehicle(self, mock_delete, mock_find, mock_session):
        mock_session.return_value = MOCK_ADMIN
        mock_find.return_value = MOCK_VEHICLE.copy()
        mock_delete.return_value = True
        response = client.delete("/vehicles/AB12CD", headers={"Authorization": "admin-token"})
        assert response.status_code == 200
        mock_delete.assert_called_once()

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.load_vehicle_data_from_db")
    def test_delete_nonexistent_vehicle(self, mock_load, mock_session):
        mock_session.return_value = MOCK_USER
        mock_load.return_value = []
        response = client.delete("/vehicles/ZZ99ZZ", headers={"Authorization": "user-token"})
        assert response.status_code == 404
        assert "Vehicle not found" in response.text


class TestGetVehicleReservation:
    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.find_vehicle_by_license_plate")
    def test_get_own_vehicle_reservations(self, mock_find, mock_session):
        mock_session.return_value = MOCK_USER
        mock_find.return_value = MOCK_VEHICLE.copy()
        response = client.get("/vehicles/AB12CD/reservations", headers={"Authorization": "valid-token"})
        assert response.status_code == 200
        data = response.json()
        assert "reservations" in data
        assert isinstance(data["reservations"], list)

    @patch("endpoints.vehicles_endpoint.get_session")
    def test_get_vehicle_reservations_unauthorized(self, mock_session):
        mock_session.return_value = None
        response = client.get("/vehicles/AB12CD/reservations")
        assert response.status_code == 401
        assert "Unauthorized" in response.text

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.find_vehicle_by_license_plate")
    def test_get_other_user_vehicle_reservations_forbidden(self, mock_find, mock_session):
        mock_session.return_value = MOCK_USER
        mock_find.return_value = MOCK_VEHICLE_2.copy()
        response = client.get("/vehicles/XY99ZZ/reservations", headers={"Authorization": "user-token"})
        assert response.status_code == 403
        assert "Forbidden" in response.text

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.load_vehicle_data_from_db")
    def test_get_reservations_nonexistent_vehicle(self, mock_load, mock_session):
        mock_session.return_value = MOCK_USER
        mock_load.return_value = []
        response = client.get("/vehicles/ZZ99ZZ/reservations", headers={"Authorization": "user-token"})
        assert response.status_code == 404
        assert "Vehicle not found" in response.text


class TestGetVehicleHistory:
    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.find_vehicle_by_license_plate")
    @patch("utils.storage_utils.load_parking_lot_data")
    @patch("utils.storage_utils.load_parking_session_data")
    def test_get_own_vehicle_history(self, mock_load_sessions, mock_load_lots, mock_find, mock_session):
        mock_session.return_value = MOCK_USER
        mock_find.return_value = MOCK_VEHICLE.copy()
        mock_load_lots.return_value = {"1": {"name": "Test Parking Lot", "address": "123 Test St"}}
        mock_load_sessions.return_value = {
            "1": {
                "licenseplate": "AB-12-CD",
                "started": "2024-01-01T10:00:00",
                "stopped": "2024-01-01T12:00:00",
                "user": "testuser",
                "duration_minutes": 120,
                "cost": 10.0,
                "payment_status": "Pending",
            }
        }
        response = client.get("/vehicles/AB12CD/history", headers={"Authorization": "valid-token"})
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)

    @patch("endpoints.vehicles_endpoint.get_session")
    def test_get_vehicle_history_unauthorized(self, mock_session):
        mock_session.return_value = None
        response = client.get("/vehicles/AB12CD/history")
        assert response.status_code == 401
        assert "Unauthorized" in response.text

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.find_vehicle_by_license_plate")
    def test_get_other_user_vehicle_history_forbidden(self, mock_find, mock_session):
        mock_session.return_value = MOCK_USER
        mock_find.return_value = MOCK_VEHICLE_2.copy()
        response = client.get("/vehicles/XY99ZZ/history", headers={"Authorization": "user-token"})
        assert response.status_code == 403
        assert "Forbidden" in response.text

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.load_vehicle_data_from_db")
    def test_get_history_nonexistent_vehicle(self, mock_load, mock_session):
        mock_session.return_value = MOCK_USER
        mock_load.return_value = []
        response = client.get("/vehicles/ZZ99ZZ/history", headers={"Authorization": "user-token"})
        assert response.status_code == 404
        assert "Vehicle not found" in response.text

    @patch("endpoints.vehicles_endpoint.get_session")
    @patch("endpoints.vehicles_endpoint.find_vehicle_by_license_plate")
    @patch("utils.storage_utils.load_parking_lot_data")
    @patch("utils.storage_utils.load_parking_session_data")
    def test_get_vehicle_history_admin_access(
        self, mock_load_sessions, mock_load_lots, mock_find, mock_session
    ):
        mock_session.return_value = MOCK_ADMIN
        mock_find.return_value = MOCK_VEHICLE.copy()
        mock_load_lots.return_value = {}
        mock_load_sessions.return_value = {}
        response = client.get("/vehicles/AB12CD/history", headers={"Authorization": "admin-token"})
        assert response.status_code == 200
        data = response.json()
        assert "history" in data


class TestNormalizePlate:
    def test_normalize_plate_with_dashes(self):
        assert normalize_plate("AB-12-CD") == "AB12CD"

    def test_normalize_plate_lowercase(self):
        assert normalize_plate("ab-12-cd") == "AB12CD"

    def test_normalize_plate_with_spaces(self):
        assert normalize_plate(" AB-12-CD ") == "AB12CD"

    def test_normalize_plate_empty(self):
        assert normalize_plate("") == ""

    def test_normalize_plate_none(self):
        assert normalize_plate(None) == ""
