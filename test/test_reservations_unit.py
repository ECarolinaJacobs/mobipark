from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch
import copy

client = TestClient(app)

MOCK_USER = {"username": "testuser", "role": "USER"}

MOCK_ADMIN = {"username": "testuser", "role": "ADMIN"}

MOCK_UNAUTHORIZED_USER = {"username": "unauthorized_user", "role": "USER"}

MOCK_RESERVATION = {
    "user_id": "testuser",
    "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
    "start_time": "2025-12-06T10:00",
    "end_time": "2025-12-07T12:00",
    "parking_lot_id": "1",
    "id": "1",
    "status": "confirmed",
}

MOCK_RESERVATION_ADMIN = {
    "user_id": "testuser",
    "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
    "start_time": "2025-12-06T10:00",
    "end_time": "2025-12-07T12:00",
    "parking_lot_id": "1",
    "id": "1",
    "status": "confirmed",
}


MOCK_VEHICLE = {
    "id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
    "user_id": "testuser",
    "license_plate": "AB-80-62",
    "make": "Opel",
    "model": "Crs",
    "color": "Pink",
    "year": 2022,
    "created_at": "2026-01-11T17:18:10.294276",
}

MOCK_PARKING_LOT = {"1": {"id": "1", "name": "TEST", "capacity": 300, "reserved": 109}}

MOCK_PARKING_LOT_FULL = {
    "1": {
        "id": "1",
        "name": "TEST",
        "capacity": 100,
        "reserved": 100,
    }
}



class TestCreateReservations:

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_missing_auth(self, mock_load_parking_data, mock_get_session):

        mock_get_session.return_value = None
        mock_load_parking_data.return_value = MOCK_PARKING_LOT

        response = client.post(
            "/reservations/",
            json=MOCK_RESERVATION,
            headers={"Authorization": "invalid_token"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired session token"
          
    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_unable_to_load_reservation_data_create(self, mock_load_reservation_data, mock_get_session):

        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = None
        
        response = client.post(
            "/reservations/",
            json=MOCK_RESERVATION,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 500
        response_data = response.json()
        assert response_data["detail"] == "Error loading data"

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_unable_to_load_parking_lot_data_create(self, mock_load_parking_lot_data, mock_get_session):

        mock_get_session.return_value = MOCK_USER
        mock_load_parking_lot_data.return_value = None
        
        response = client.post(
            "/reservations/",
            json=MOCK_RESERVATION,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 500
        response_data = response.json()
        assert response_data["detail"] == "Error loading data"

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_load_reservation_data_exception_create(
        self, mock_load_reservation_data, mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.side_effect = Exception("Error loading data")

        response = client.post(
            "/reservations/",
            json=MOCK_RESERVATION,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 500
        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_load_parking_lot_data_exception_create(
        self, mock_load_parking_lot_data, mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_parking_lot_data.side_effect = Exception("Error loading data")

        response = client.post(
            "/reservations/",
            json=MOCK_RESERVATION,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 500
        mock_load_parking_lot_data.assert_called_once()   

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_create_reservation_success(
        self,
        mock_load_parking_data,
        mock_save_parking_data,
        mock_save_reservation_data,
        load_reservation_data,
        mock_get_session,
    ):

        mock_get_session.return_value = MOCK_USER
        load_reservation_data.return_value = []
        mock_load_parking_data.return_value = copy.deepcopy(MOCK_PARKING_LOT)
        mock_save_parking_data.return_value = []

        response = client.post(
            "/reservations/",
            json=MOCK_RESERVATION,
            headers={"Authorization": "valid_token"},
        )

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["status"] == "Success"

        saved_parking_lots = mock_save_parking_data.call_args[0][0]
        assert saved_parking_lots["1"]["reserved"] == 110
        
        reservation = response_data["reservation"]
        assert "id" in reservation
        assert "vehicle_id" in reservation
        assert "start_time" in reservation
        assert "end_time" in reservation
        assert "parking_lot_id" in reservation
        assert "created_at" in reservation
        mock_save_reservation_data.assert_called_once()
        mock_load_parking_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_create_reservation_success_admin(
        self,
        mock_load_parking_data,
        mock_save_parking_data,
        mock_save_reservation_data,
        load_reservation_data,
        mock_get_session,
    ):

        mock_get_session.return_value = MOCK_ADMIN
        load_reservation_data.return_value = []
        mock_load_parking_data.return_value = copy.deepcopy(MOCK_PARKING_LOT)
        mock_save_parking_data.return_value = []
    

        response = client.post(
            "/reservations/",
            json=MOCK_RESERVATION_ADMIN,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["status"] == "Success"

        saved_parking_lots = mock_save_parking_data.call_args[0][0]
        assert saved_parking_lots["1"]["reserved"] == 110

        reservation = response_data["reservation"]
        assert "id" in reservation
        assert "user_id" in reservation
        assert "vehicle_id" in reservation
        assert "start_time" in reservation
        assert "end_time" in reservation
        assert "parking_lot_id" in reservation
        assert "created_at" in reservation
        mock_save_reservation_data.assert_called_once()
        mock_load_parking_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_create_reservation_admin_without_user_id(
        self, mock_load_parking_data, load_reservation_data, mock_get_session
    ):

        mock_get_session.return_value = MOCK_ADMIN
        load_reservation_data.return_value = []
        mock_load_parking_data.return_value = copy.deepcopy(MOCK_PARKING_LOT)

        copy_mock_reservation = copy.deepcopy(MOCK_RESERVATION_ADMIN)
        copy_mock_reservation["user_id"] = None

        response = client.post(
            "/reservations/",
            json=copy_mock_reservation,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 401

        mock_load_parking_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    def test_create_reservation_parking_lot_full(
        self,
        mock_save_parking_data,
        mock_load_parking_data,
        mock_save_reservation_data,
        load_reservation_data,
        mock_get_session,
    ):

        mock_get_session.return_value = MOCK_USER
        load_reservation_data.return_value = []
        mock_load_parking_data.return_value = copy.deepcopy(MOCK_PARKING_LOT_FULL)

        mock_save_parking_data.return_value = []

        response = client.post(
            "/reservations/",
            json=MOCK_RESERVATION,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 409

        response_data = response.json()
        assert response_data["detail"] == "Parking lot is currently full"

        mock_save_reservation_data.assert_not_called()
        mock_load_parking_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    def test_get_reservation_id_with_no_existing_reservations(
        self, mock_save_parking_lot_data,mock_load_parking_lot_data, mock_save_reservation_data, mock_load_reservation_data, mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = []
        mock_load_parking_lot_data.return_value = copy.deepcopy(MOCK_PARKING_LOT)

        response = client.post(
            "/reservations/",
            json=MOCK_RESERVATION,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 201
        assert response.json()["reservation"]["id"] == "1"

        mock_load_reservation_data.assert_called_once()
        mock_save_reservation_data.assert_called_once()
        mock_save_parking_lot_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_missing_parking_lot_id(self, mock_load_reservation_data, mock_get_session):

        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = []

        copy_mock_reservation =copy.deepcopy(MOCK_RESERVATION)
        copy_mock_reservation["parking_lot_id"] = "5678"


        response = client.post(
            "/reservations/",
            json=copy_mock_reservation,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 404

        response_data = response.json()
        assert response_data["detail"] == "Parking lot not found"

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_parkinglot_not_found(self, mock_load_reservation_data, mock_get_session):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = []

        response = client.post(
            "/reservations/1",
            json=MOCK_RESERVATION,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 405

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_invalid_reservation_data(
        self, mock_load_reservation_data, mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = []

        copy_mock_reservation = copy.deepcopy(MOCK_RESERVATION)
        copy_mock_reservation["start_time"] = None

        response = client.post(
            "/reservations/",
            json=copy_mock_reservation,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 422

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_create_reservations_invalid_start_time(
        self,
        mock_load_reservation_data,
        mock_get_session):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = []
        copy_mock_reservation = copy.deepcopy(MOCK_RESERVATION)
        copy_mock_reservation["start_time"] = "invalid-format"
        
        response = client.post("/reservations/", json=copy_mock_reservation, headers={"Authorization": "valid_token"})
        assert response.status_code == 422
        assert "start_time" in response.json()["detail"][0]["loc"]
        assert response.json()["detail"][0]["msg"] == "Value error, Date must be in iso format: YYYY-MM-DDTHH:MM"
    
    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_create_reservations_invalid_end_time(
        self,
        mock_load_reservation_data,
        mock_get_session):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = []
        copy_mock_reservation = copy.deepcopy(MOCK_RESERVATION)
        copy_mock_reservation["end_time"] = "invalid-format"
        
        response = client.post("/reservations/", json=copy_mock_reservation, headers={"Authorization": "valid_token"})
        assert response.status_code == 422
        assert "end_time" in response.json()["detail"][0]["loc"]
        assert response.json()["detail"][0]["msg"] == "Value error, Date must be in iso format: YYYY-MM-DDTHH:MM"

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_end_time_before_start_time_create(self,mock_load_parking_data, mock_load_reservation_data, mock_get_session):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = []
        mock_load_parking_data.return_value = copy.deepcopy(MOCK_PARKING_LOT)

        copy_mock_reservation = copy.deepcopy(MOCK_RESERVATION)
        copy_mock_reservation["start_time"] = "2025-12-07T10:00"
        copy_mock_reservation["end_time"] = "2025-12-06T12:00"

        response = client.post(
            "/reservations/",
            json=copy_mock_reservation,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 422

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_create_reservation_parking_lot_full_but_time_available(
        self,
        mock_load_parking_data,
        mock_save_parking_data,
        mock_save_reservation_data,
        load_reservation_data,
        mock_get_session,
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_parking_data.return_value = copy.deepcopy(MOCK_PARKING_LOT_FULL)

        mock_save_parking_data.return_value = []
        load_reservation_data.return_value = [MOCK_RESERVATION]
    
        new_reservation = [
            {
                "user_id": "testuser",
                "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
                "start_time": "2025-12-07T13:00",
                "end_time": "2025-12-07T14:00",
                "parking_lot_id": "1",
                "id": "2",
            }
        ]

        response = client.post(
            "/reservations/",
            json=new_reservation[0],
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["status"] == "Success"

        saved_parking_lots = mock_save_parking_data.call_args[0][0]
        assert saved_parking_lots["1"]["reserved"] == 101

        reservation = response_data["reservation"]
        assert "id" in reservation
        assert "vehicle_id" in reservation
        assert "start_time" in reservation
        assert "end_time" in reservation
        assert "parking_lot_id" in reservation
        assert "created_at" in reservation
        mock_save_reservation_data.assert_called_once()
        mock_load_parking_data.assert_called_once()
    
    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_create_reservation_fetch_correct_time_available(
        self,
        mock_load_parking_data,
        mock_save_parking_data,
        mock_save_reservation_data,
        load_reservation_data,
        mock_get_session,
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_parking_data.return_value = copy.deepcopy(MOCK_PARKING_LOT_FULL)

        mock_save_parking_data.return_value = []
        load_reservation_data.return_value = [
            MOCK_RESERVATION,      
        {
            "user_id": "testuser",
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-06T10:00",
            "end_time": "2025-12-07T14:00",
            "parking_lot_id": "1",
            "id": "1",
            "status": "confirmed",
        }
        ]
     
        {
            "user_id": "testuser",
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-06T10:00",
            "end_time": "2025-12-07T14:00",
            "parking_lot_id": "1",
            "id": "1",
            "status": "confirmed",
        }

        new_reservation = [
            {
                "user_id": "testuser",
                "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
                "start_time": "2025-12-07T13:00",
                "end_time": "2025-12-07T14:00",
                "parking_lot_id": "1",
                "id": "2",
            }
        ]

        response = client.post(
            "/reservations/",
            json=new_reservation[0],
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["status"] == "Success"

        saved_parking_lots = mock_save_parking_data.call_args[0][0]
        assert saved_parking_lots["1"]["reserved"] == 101

        reservation = response_data["reservation"]
        assert "id" in reservation
        assert "vehicle_id" in reservation
        assert "start_time" in reservation
        assert "end_time" in reservation
        assert "parking_lot_id" in reservation
        assert "created_at" in reservation
        mock_save_reservation_data.assert_called_once()
        mock_load_parking_data.assert_called_once()
    
    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    def test_create_reservation_parking_lot_full_and_time_unavailable(
        self,
        mock_save_parking_data, 
        mock_load_parking_data,
        load_reservation_data,
        mock_get_session,
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_parking_data.return_value = copy.deepcopy(MOCK_PARKING_LOT_FULL)

        mock_save_parking_data.return_value = []
        load_reservation_data.return_value = [MOCK_RESERVATION]
    
        new_reservation = [
            {
                "user_id": "testuser",
                "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
                "start_time": "2024-01-07T13:00",
                "end_time": "2024-01-07T14:00",
                "parking_lot_id": "1",
                "id": "2",
            }
        ]

        response = client.post(
            "/reservations/",
            json=new_reservation[0],
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == f"Parking lot is full. Earliest available time is {MOCK_RESERVATION['end_time']}"
   
        mock_load_parking_data.assert_called_once()

class TestGetReservations:

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_get_reservations_success(
        self, mock_load_reservation_data, mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]

        response = client.get(
            f"/reservations/{MOCK_RESERVATION['id']}",
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1

        reservation = data["reservation"]
        assert isinstance(reservation, dict)
        assert reservation["user_id"] == "testuser"
        assert reservation["vehicle_id"] == MOCK_RESERVATION["vehicle_id"]
        assert reservation["start_time"] == MOCK_RESERVATION["start_time"]
        assert reservation["end_time"] == MOCK_RESERVATION["end_time"]
        assert reservation["parking_lot_id"] == MOCK_RESERVATION["parking_lot_id"]
        assert reservation["id"] == "1"

        mock_load_reservation_data.assert_called_once()
        
    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_get_reservations_success_admin(
        self,
        mock_load_reservation_data,
        mock_get_session
    ):
        mock_get_session.return_value = MOCK_ADMIN
        mock_load_reservation_data.return_value = [MOCK_RESERVATION_ADMIN]

        response = client.get(
            f"/reservations/{MOCK_RESERVATION_ADMIN['id']}",
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1

        reservation = data["reservation"]
        assert isinstance(reservation, dict)
        assert reservation["user_id"] == "testuser"
        assert reservation["vehicle_id"] == MOCK_RESERVATION_ADMIN["vehicle_id"]
        assert reservation["start_time"] == MOCK_RESERVATION_ADMIN["start_time"]
        assert reservation["end_time"] == MOCK_RESERVATION_ADMIN["end_time"]
        assert reservation["parking_lot_id"] == MOCK_RESERVATION_ADMIN["parking_lot_id"]
        assert reservation["id"] == "1"

        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_get_reservation_not_found(
        self,
        mock_load_reservation_data,
        mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = []

        response = client.get(
            "/reservations/99999999999999", headers={"Authorization": "valid_token"}
        )
        assert response.status_code == 404

        data = response.json()
        assert data["detail"] == "Reservation not found"

        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_get_reservation_unauthorized(
        self,
        mock_load_reservation_data,
        mock_get_session
    ):
        mock_get_session.return_value = MOCK_UNAUTHORIZED_USER
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]

        response = client.get(
            f"/reservations/{MOCK_RESERVATION['id']}",
            headers={"Authorization": "unauthorized_token"},
        )
        assert response.status_code == 403

        mock_load_reservation_data.assert_called_once()


class TestUpdateReservations:

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_missing_auth_update(self, mock_load_parking_data, mock_get_session):

        mock_get_session.return_value = None
        mock_load_parking_data.return_value = copy.deepcopy(MOCK_PARKING_LOT)

        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=MOCK_RESERVATION,
            headers={"Authorization": "invalid_token"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing Authorization header"

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_missing_auth_update(self, mock_load_parking_data, mock_get_session):

        mock_get_session.return_value = None
        mock_load_parking_data.return_value = MOCK_PARKING_LOT

        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=MOCK_RESERVATION,
            headers={"Authorization": "invalid_token"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired session token"

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_unable_to_load_parking_lot_data_update(self, mock_load_parking_data, mock_get_session):

        mock_get_session.return_value = MOCK_USER
        mock_load_parking_data.return_value = None

        updated_data = {
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "1",
        }
        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 500
        response_data = response.json()
        assert response_data["detail"] == "Error loading data"
    
    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_unable_to_load_reservation_data_update(self, mock_load_reservation_data, mock_get_session):

        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = None

        updated_data = {
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "1",
        }

        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 500
        response_data = response.json()
        assert response_data["detail"] == "Error loading data"
        
    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_end_time_before_start_time_update(self, mock_load_reservation_data, mock_get_session):

        copy_mock_reservation = copy.deepcopy(MOCK_RESERVATION)
        copy_mock_reservation["start_time"] = "2025-12-07T10:00"
        copy_mock_reservation["end_time"] = "2025-12-06T12:00"

        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]

        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=copy_mock_reservation,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 422

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_load_reservation_data_exception_update(
        self, mock_load_reservation_data, mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.side_effect = Exception("Error loading data")

        updated_data = {
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "1",
        }
        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 500
        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_parking_lot_data")
    def test_load_parking_lot_data_exception_update(
        self, mock_load_parking_lot_data, mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_parking_lot_data.side_effect = Exception("Error loading data")
        updated_data = {
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "1",
        }
        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 500
        mock_load_parking_lot_data.assert_called_once() 

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    def test_update_reservation_success(
        self,
        mock_save_parking_lot_data,
        mock_load_parking_data,
        mock_save_reservation_data,
        mock_load_reservation_data,
        mock_get_session,
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]
        mock_load_parking_data.return_value = MOCK_PARKING_LOT
        mock_save_reservation_data.return_value = None
        mock_save_parking_lot_data.return_value = None

        updated_data = {
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "1",
        }

        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "Updated"

        reservation = data["reservation"]
        assert reservation["start_time"] == updated_data["start_time"]

        mock_save_reservation_data.assert_called_once()
        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    def test_update_reservation_success_admin(
        self,
        mock_save_parking_lot_data,
        mock_load_parking_data,
        mock_save_reservation_data,
        mock_load_reservation_data,
        mock_get_session
    ):
        mock_get_session.return_value = MOCK_ADMIN
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]
        mock_load_parking_data.return_value = MOCK_PARKING_LOT

        updated_data = {
            "user_id": "testuser",
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "1",
            "cost": 75,
            "status": "confirmed",
            "id": "1",
        }

        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "Updated"
        reservation = data["reservation"]
        assert reservation["start_time"] == updated_data["start_time"]
        assert reservation["end_time"] == updated_data["end_time"]

        mock_save_reservation_data.assert_called_once()
        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_update_reservation_not_found(
        self, mock_load_reservation_data, mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = []

        updated_data = {
            "user_id": "testuser",
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "1",
            "id": "1",
        }

        response = client.put(
            "/reservations/99999999999999",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 404

        data = response.json()
        assert data["detail"] == "Reservation not found"

        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_update_reservation_unauthorized(
        self,
        mock_load_reservation_data,
        mock_get_session
    ):
        mock_get_session.return_value = MOCK_UNAUTHORIZED_USER
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]

        updated_data = {
            "user_id": "testuser",
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "1",
            "id": "1",
        }

        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "unauthorized_token"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_unauthorized_update_cost(
        self,
        mock_load_reservation_data,
        mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]

        updated_data = {
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "1",
            "cost": 50,
            "id": "1",
        }

        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Only admins can modify reservation cost"

        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_unauthorized_update_status(
        self,
        mock_load_reservation_data,
        mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]

        updated_data = {
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "1",
            "status": "Cancelled",
            "id": "1",
        }

        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Only admins can modify reservation status"

        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_new_parking_lot_not_found(
        self,
        mock_load_reservation_data,
        mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]

        updated_data = {
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "9999",
            "id": "1",
        }

        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 404

        data = response.json()
        assert data["detail"] == "New parking lot not found"

        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    def test_update_parking_lot(
        self,
        mock_save_parking_lot_data,
        mock_load_parking_lot_data,
        mock_save_reservation_data,
        mock_load_reservation_data,
        mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]
    
        mock_load_parking_lot_data.return_value = {
            "1": {
                "id": "1",
                "name": "TEST_FULL",
                "capacity": 100,
                "reserved": 100,
            },
            "2": {
                "id": "2",
                "name": "TEST_AVAILABLE",
                "capacity": 300,
                "reserved": 109
            }
        }
        updated_data = {
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "2",
            "id": "1",
        }
        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
       
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "Updated"

        saved_parking_lots = mock_save_parking_lot_data.call_args[0][0]
        assert saved_parking_lots["1"]["reserved"] == 99
        assert saved_parking_lots["2"]["reserved"] == 110

        mock_save_reservation_data.assert_called_once()
    
    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_update_reservation_invalid_status(self, mock_load_reservation_data,mock_get_session):
        mock_get_session.return_value = MOCK_ADMIN
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]
        updated_data = {
            "vehicle_id": "7abb4afe-cfb3-4b8a-bda3-3723a33ab144",
            "start_time": "2025-12-08T10:00",
            "end_time": "2025-12-09T12:00",
            "parking_lot_id": "1",
            "status": "InvalidStatus",
            "id": "1",
        }

        response = client.put(
            f"/reservations/{MOCK_RESERVATION['id']}",
            json=updated_data,
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid status"

class TestDeleteReservations:
    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    def test_delete_reservation_success(
        self,
        mock_save_parking_lot_data,
        mock_load_parking_lot_data,
        mock_save_reservation_data,
        mock_load_reservation_data,
        mock_get_session,
    ):
        mock_get_session.return_value = MOCK_USER
        mock_reservation = copy.deepcopy(MOCK_RESERVATION)
        mock_load_reservation_data.return_value = [mock_reservation]
        mock_load_parking_lot_data.return_value = copy.deepcopy(MOCK_PARKING_LOT)

        response = client.delete(
            f"/reservations/{mock_reservation['id']}",
            headers={"Authorization": "valid_token"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Deleted"

        saved_parking_lot_data = mock_save_parking_lot_data.call_args[0][0]
        assert saved_parking_lot_data["1"]["reserved"] == 108

        assert data["id"] == MOCK_RESERVATION["id"]

        mock_save_reservation_data.assert_called_once()
        mock_save_parking_lot_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    @patch("endpoints.reservations.load_parking_lot_data")
    @patch("endpoints.reservations.save_parking_lot_data")
    def test_delete_reservation_success_admin(
        self,
        mock_save_parking_lot_data,
        mock_load_parking_lot_data,
        mock_save_reservation_data,
        mock_load_reservation_data,
        mock_get_session,
    ):
        mock_get_session.return_value = MOCK_ADMIN
        mock_reservation = copy.deepcopy(MOCK_RESERVATION)
        mock_load_reservation_data.return_value = [mock_reservation]
        mock_load_parking_lot_data.return_value = copy.deepcopy(MOCK_PARKING_LOT)

        response = client.delete(
            f"/reservations/{mock_reservation['id']}",
            headers={"Authorization": "valid_token"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Deleted"
        assert data["id"] == mock_reservation["id"]
      
        args, _ = mock_save_parking_lot_data.call_args
        saved_parking_data = args[0]
        assert saved_parking_data["1"]["reserved"] == 108
        

        mock_save_reservation_data.assert_called_once()
        mock_save_parking_lot_data.assert_called_once()
    
    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    @patch("endpoints.reservations.save_reservation_data")
    def test_delete_reservation_not_found(
        self,
        mock_load_parking_lot_data,
        mock_load_reservation_data,
        mock_get_session
    ):
        mock_get_session.return_value = MOCK_USER
        mock_load_reservation_data.return_value = []
        mock_load_parking_lot_data.return_value = copy.deepcopy(MOCK_PARKING_LOT)
        mock_load_parking_lot_data
        response = client.delete(
            "/reservations/99999999999999",
            headers={"Authorization": "valid_token"},
        )
        assert response.status_code == 404 
        data = response.json()
        assert data["detail"] == "Reservation not found"
        mock_load_reservation_data.assert_called_once()

    @patch("endpoints.reservations.get_session")
    @patch("endpoints.reservations.load_reservation_data")
    def test_delete_reservation_unauthorized(
        self,
        mock_load_reservation_data,
        mock_get_session
    ):
        mock_get_session.return_value = MOCK_UNAUTHORIZED_USER
        mock_load_reservation_data.return_value = [MOCK_RESERVATION]

        response = client.delete(
            f"/reservations/{MOCK_RESERVATION['id']}",
            headers={"Authorization": "unauthorized_token"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

        mock_load_reservation_data.assert_called_once()
        