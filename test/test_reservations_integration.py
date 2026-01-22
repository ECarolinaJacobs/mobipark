import pytest
import json
from test.test_utils import create_user, get_session
import random
import os


ADMIN_LOGIN = {"username": "admin", "password": "admin"}

USER_LOGIN = {"username": "test", "password": "test"}


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """ensure using mock data for all tests"""
    os.environ["USE_MOCK_DATA"] = "true"
    yield


@pytest.fixture(scope="session", autouse=True)
def ensure_parking_lot_exists(client):
    try:
        create_user(True, username=ADMIN_LOGIN["username"], password=ADMIN_LOGIN["password"], client=client)
    except Exception:
        pass

    try:
        headers = get_session(username=ADMIN_LOGIN["username"], password=ADMIN_LOGIN["password"], client=client)
    except KeyError:
         # Fallback if create_user didn't work as expected or user persists
         pass
    
    # Check if lot with ID 1 exists
    try:
        res = client.get("/parking-lots/1")
        if res.status_code == 200:
            return
    except Exception:
        pass

    # If 1 doesn't exist, we might have higher IDs. Delete all to reset ID counter (if implementation allows)
    # The implementation uses max(id) + 1. So deleting all resets to 1.
    try:
        res = client.get("/parking-lots/")
        if res.status_code == 200:
            lots = res.json()
            headers = get_session(username=ADMIN_LOGIN["username"], password=ADMIN_LOGIN["password"], client=client)
            for lot in lots:
                client.delete(f"/parking-lots/{lot['id']}", headers=headers)
    except Exception:
        pass

    # Create it
    lot_data = {
            "name": "RESERVATION_TEST_LOT",
            "location": "TEST_LOCATION",
            "address": "TEST_ADDRESS",
            "capacity": 100,
            "reserved": 0,
            "tariff": 2.50,
            "daytariff": 20.00,
            "created_at": "2025-01-01",
            "coordinates": {"lat": 0.0, "lng": 0.0},
    }
    
    try:
        headers = get_session(username=ADMIN_LOGIN["username"], password=ADMIN_LOGIN["password"], client=client)
        client.post("/parking-lots/", json=lot_data, headers=headers)
    except Exception as e:
        print(f"Failed to create parking lot: {e}")



@pytest.fixture(scope="session")
def vehicle_creation_succes(client):
    try:
        create_user(False, client=client)
    except Exception as e:
        print(f"Error creating user: {e}")

    headers = get_session(client=client)
    unique_plate = f"AB-{random.randint(10, 99)}-{random.randint(10, 99)}"
    vehicle_data = {
        "user_id": "TestUser",
        "license_plate": unique_plate,
        "make": "Opel",
        "model": "Crs",
        "color": "Pink",
        "year": 2022,
    }
    res = client.post("/vehicles", json=vehicle_data, headers=headers)

    vehicle = {}
    if res.status_code == 200:
        vehicle = res.json()
    elif res.status_code == 400 and "already exists" in res.json().get("detail", ""):
        res_get = client.get("/vehicles", headers=headers)
        if res_get.status_code == 200 and res_get.json():
            for v in res_get.json():
                if v.get("license_plate") == unique_plate:
                    vehicle = v
                    break
        if not vehicle:
            pytest.skip("Could not create or retrieve vehicle for test user.")
    else:
        pytest.fail(f"Vehicle creation failed with status {res.status_code}: {res.json()}")

    assert "id" in vehicle, "Vehicle fixture failed to provide a vehicle with an 'id'"

    yield vehicle, headers

    if "id" in vehicle:
        client.delete(f"/vehicles/{vehicle['id']}", headers=headers)

    # delete_user()


@pytest.fixture(scope="session")
def vehicle_creation_succes_admin(client):
    try:
        create_user(True, username=ADMIN_LOGIN["username"], password=ADMIN_LOGIN["password"], client=client)
    except Exception as e:
        print(f"User 'admin' might already exist: {e}")

    headers = get_session(username=ADMIN_LOGIN["username"], password=ADMIN_LOGIN["password"], client=client)

    unique_plate = f"AB-{random.randint(10, 99)}-{random.randint(10, 99)}"
    vehicle_data = {
        "user_id": "AdminUser",
        "license_plate": unique_plate,
        "make": "BMW",
        "model": "X5",
        "color": "pink",
        "year": 2023,
    }
    res = client.post("/vehicles", json=vehicle_data, headers=headers)

    vehicle = {}
    if res.status_code == 200:
        vehicle = res.json()
    elif res.status_code == 400 and "already exists" in res.json().get("detail", ""):
        res_get = client.get("/vehicles", headers=headers)
        if res_get.status_code == 200 and res_get.json():
            for v in res_get.json():
                if v.get("license_plate") == unique_plate:
                    vehicle = v
                    break
        if not vehicle:
            pytest.skip("Could not create or retrieve vehicle for admin user.")
    else:
        pytest.fail(f"Admin vehicle creation failed with status {res.status_code}: {res.json()}")

    assert "id" in vehicle, "Admin vehicle fixture failed to provide a vehicle with an 'id'"

    yield vehicle, headers

    if "id" in vehicle:
        client.delete(f"/vehicles/{vehicle['id']}", headers=headers)

    # delete_user(username=ADMIN_LOGIN["username"])


# ======================================================================================
"""POST reservations endpoint tests"""

#Test if a user is able to create a reservation
def test_create_reservation_as_user(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res = client.post("/reservations/", json=data, headers=headers)
    assert res.status_code == 201
    assert res.json()["status"] == "Success"
    reservation = res.json()["reservation"]
    assert reservation["vehicle_id"] == data["vehicle_id"]
    assert reservation["user_id"] == USER_LOGIN["username"]

#Test if an admin is able to create a reservation
def test_create_reçservation_as_admin(client, vehicle_creation_succes_admin):
    vehicle, headers = vehicle_creation_succes_admin
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
        "user_id": USER_LOGIN["username"],
    }
    res = client.post("/reservations/", json=data, headers=headers)

    assert res.status_code == 201
    assert res.json()["status"] == "Success"
    reservation = res.json()["reservation"]
    for key in data:
        assert reservation[key] == data[key]

#Test if there is a 404 when admin didnt give the user_id when creating a reservating
def test_create_reservation_as_admin_missing_user(client, vehicle_creation_succes_admin):
    vehicle, headers = vehicle_creation_succes_admin
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res = client.post("/reservations/", json=data, headers=headers)

    assert res.status_code == 401
    assert res.json()["error"] == "Required field missing"
    assert res.json()["field"] == "user_id"

#Test to see when the required parking lot is missing when creating a reservation, it gives a 422 error back with details.
def test_missing_parking_lot(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00", "end_time": "2025-12-06T12:00"}
    res = client.post("/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert res.json()["detail"][0]["type"] == "missing"
    assert res.json()["detail"][0]["loc"][-1] == "parking_lot_id"

#Test to see when the required vehicle id is missing when creating a reservation, it gives a 422 error back with details.
def test_missing_vehicle_id(client):
    create_user(False, client=client)
    headers = get_session(client=client)
    data = {"start_time": "2025-12-06T10:00", "end_time": "2025-12-06T12:00", "parking_lot_id": "1"}
    res = client.post("/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert res.json()["detail"][0]["type"] == "missing"
    assert res.json()["detail"][0]["loc"][-1] == "vehicle_id"

#Test to see when the required start time is missing when creating a reservation, it gives a 422 error back with details.
def test_missing_start_time(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "end_time": "2025-12-06T12:00", "parking_lot_id": "1"}
    res = client.post("/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert res.json()["detail"][0]["type"] == "missing"
    assert res.json()["detail"][0]["loc"][-1] == "start_time"

#Test to see when the required vehicle id is incorrect when creating a reservation, it gives a 422 error back with details.
def test_incorrect_vehicle_id_format(client):
    create_user(False, client=client)
    headers = get_session(client=client)
    #Incorrect vehicle id format.
    data = {
        "vehicle_id": "1233456",
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res = client.post("/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert "Vehicle id must be a valid uuid" in res.json()["detail"][0]["msg"]
    assert res.json()["detail"][0]["loc"][-1] == "vehicle_id"
    # delete_user()

#Test to see when the required start time is incorrect when creating a reservation, it gives a 422 error back with details.
def test_incorrect_start_time_format(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    #Incorrect start time format.
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "123456789",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res = client.post("/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert "Value error, Date must be in iso format: YYYY-MM-DDTHH:MM" in res.json()["detail"][0]["msg"]

#Test to see when the required parking lot id is incorrect when creating a reservation, it gives a 422 error back with details.
def test_incorrect_parking_lot_id_format(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    #Incorrect parking lot id.
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "Z",
    }
    res = client.post("/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert "Parking lot id must be a digit" in res.json()["detail"][0]["msg"]

#Test if the test gives an error when the user gives a nonexisting parking lot id is given when creating a reservation.
def test_parking_lot_id_not_found_user(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    #parking_lot_id does not exist.
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "99999",
    }
    res = client.post("/reservations/", json=data, headers=headers)

    assert res.status_code == 404
    assert res.json()["detail"] == "Parking lot not found"

#Test if the test gives an error when the admin gives a nonexisting parking lot id is given when creating a reservation.
def test_parking_lot_id_not_found_admin(client, vehicle_creation_succes_admin):
    vehicle, headers = vehicle_creation_succes_admin
    #parking_lot_id does not exist.
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "99999",
        "user_id": "test",
    }
    res = client.post("/reservations/", json=data, headers=headers)

    assert res.status_code == 404
    assert res.json()["detail"] == "Parking lot not found"


# ======================================================================================
"""PUT reservations endpoint tests"""

#Test to see when the required vehicle id is missing when updating a reservation, it gives a 422 error back with details.
def test_update_missing_vehicle_id(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res = client.post("/reservations/", json=data, headers=headers)
    assert res.status_code == 201

    reservation_id = res.json()["reservation"]["id"]
    new_data = {"start_time": "2025-12-06T10:00", "end_time": "2025-12-06T12:00", "parking_lot_id": "1"}

    res_put = client.put(f"/reservations/{reservation_id}", json=new_data, headers=headers)

    assert res_put.status_code == 422
    assert res_put.json()["detail"][0]["type"] == "missing"
    assert res_put.json()["detail"][0]["loc"][-1] == "vehicle_id"

#Test to see when the required start time is missing when updating a reservation, it gives a 422 error back with details.
def test_update_missing_start_time(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res = client.post("/reservations/", json=data, headers=headers)
    assert res.status_code == 201

    reservation_id = res.json()["reservation"]["id"]
    new_data = {"vehicle_id": vehicle["id"], "end_time": "2025-12-06T12:00", "parking_lot_id": "1"}

    res_put = client.put(f"/reservations/{reservation_id}", json=new_data, headers=headers)

    assert res_put.status_code == 422
    assert res_put.json()["detail"][0]["type"] == "missing"
    assert res_put.json()["detail"][0]["loc"][-1] == "start_time"

#Test when a user tries to update the cost of a reservation, it gives an 403 error back with details.
def test_update_cost_as_user(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res = client.post("/reservations/", json=data, headers=headers)
    assert res.status_code == 201

    reservation_id = res.json()["reservation"]["id"]
    new_data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
        "cost": "4567890",
    }
    res_put = client.put(f"/reservations/{reservation_id}", json=new_data, headers=headers)

    assert res_put.status_code == 403
    assert "Only admins can modify reservation cost" in res_put.json()["detail"]

#Test when a user tries to update the status of a reservation, it gives an 403 error back with details.
def test_update_status_as_user(client, vehicle_creation_succes):

    #User doesn't have permission to modify reservatuon status.
    vehicle, headers = vehicle_creation_succes
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res = client.post("/reservations/", json=data, headers=headers)
    assert res.status_code == 201
    
    reservation_id = res.json()["reservation"]["id"]
    new_data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
        "status": "confirmed",
    }
    res_put = client.put(f"/reservations/{reservation_id}", json=new_data, headers=headers)

    assert res_put.status_code == 403
    assert "Only admins can modify reservation status" in res_put.json()["detail"]

#Test when admin didnt give the user_id when updating a reservation,,it gives a 404 error back with details.
def test_update_invalid_status_as_admin(client, vehicle_creation_succes_admin):
    vehicle, headers = vehicle_creation_succes_admin
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
        "user_id": vehicle["user_id"],
    }
    res = client.post("/reservations/", json=data, headers=headers)
    assert res.status_code == 201

    reservation_id = res.json()["reservation"]["id"]
    new_data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
        "status": "invalid_status",
        "user_id": vehicle["user_id"],
    }
    res_put = client.put(f"/reservations/{reservation_id}", json=new_data, headers=headers)
    assert res_put.status_code == 403
    assert "Invalid status" in res_put.json()["detail"]

#Test when trying to update a reservation and the reservation id is not found, it gives a 404 error back with details.
def test_update_reservation_not_found(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    new_data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    #Reservation id that doesn't exist.
    res = client.put(f"/reservations/9999999999999", json=new_data, headers=headers)

    assert res.status_code == 404
    assert res.json()["detail"] == "Reservation not found"


#Test if a user is able to update a reservation.
def test_update_reservation_success(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res = client.post("/reservations/", json=data, headers=headers)
    assert res.status_code == 201

    reservation_id = res.json()["reservation"]["id"]
    new_data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res_put = client.put(f"/reservations/{reservation_id}", json=new_data, headers=headers)

    assert res_put.status_code == 200
    assert res_put.json()["status"] == "Updated"
    reservation = res_put.json()["reservation"]
    for key in new_data:
        assert reservation[key] == new_data[key]




# ======================================================================================
"""DELETE reservations endpoint tests"""

#Test if a user is able to delete a reservation.
def test_delete_reservation_deletion_succes(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res = client.post("/reservations/", json=data, headers=headers)
    assert res.status_code == 201

    reservation_id = res.json()["reservation"]["id"]
    res_delete = client.delete(f"/reservations/{reservation_id}", headers=headers)

    assert res_delete.status_code == 200
    assert res_delete.json()["status"] == "Deleted"
    assert res_delete.json()["id"] == reservation_id

#Test when a user tries to delete a reservation that doesn't exist a 404 error with details.
def test_delete_reservation_not_found(client):
    create_user(False, client=client)
    headers = get_session(client=client)
    res_delete = client.delete(f"/reservations/19999999999999999", headers=headers)

    assert res_delete.status_code == 404
    assert res_delete.json()["detail"] == "Reservation not found"


# ======================================================================================
"""GET reservations endpoint tests"""

#Test if a user is able to retrieve a reservation.
def test_get_reservation_succes(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {
        "vehicle_id": vehicle["id"],
        "start_time": "2025-12-06T10:00",
        "end_time": "2025-12-06T12:00",
        "parking_lot_id": "1",
    }
    res = client.post("/reservations/", json=data, headers=headers)
    assert res.status_code == 201

    reservation_id = res.json()["reservation"]["id"]

    response = client.get(f"/reservations/{reservation_id}", headers=headers)

    assert response.status_code == 200
    reservation = response.json()["reservation"]
    assert reservation["id"] == reservation_id

#Test when a user tries to retrieve a reservation that doesn't exist a 404 error with details.
def test_get_reservation_not_found(client, vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    response = client.get(f"/reservations/9999999999999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Reservation not found"