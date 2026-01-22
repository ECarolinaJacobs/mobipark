import pytest
import json
from test.test_utils import (
    create_user,
    delete_user,
    get_session,
    delete_parking_lot,
    find_parking_lot_id_by_name,
    find_parking_session_id_by_plate,
    delete_parking_session,
    create_random_dutch_plate,
    load_parking_lots_from_mock,
    update_user_role
)
from utils import storage_utils

# TODO: TEST EDGE CASES

# POST ENDPOINTS #

# def test_create_users(client):
#     res2 = client.post("/auth/register", json={"username": "admin", "password": "admin", "name": "admin"})
#     update_user_role("admin", "ADMIN")
#     assert res2.status_code == 200

#     res = client.post("/auth/register", json={"username": "test", "password": "test", "name": "tester"})
#     assert res.status_code == 200


def test_create_parking_lot(client):
    create_user(True, "admin", "admin", client=client)
    res = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin", client=client)
    
    res = client.post(
        "/parking-lots/",
        json={
            "name": "TEST_PARKING_LOT",
            "location": "TEST_LOCATION",
            "address": "TEST_ADDRESS",
            "capacity": 10,
            "reserved": 0,
            "tariff": 2.50,
            "daytariff": 20.00,
            "created_at": "2025-12-12",
            "coordinates": {"lat": 40.712776, "lng": -74.005974},
        },
        headers=headers,
    )

    assert res.status_code == 200

    delete_parking_lot()


def test_start_and_stop_session(client):
    delete_parking_lot()
    create_user(True, "admin", "admin", client=client)
    res = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin", client=client)
    lot_res = client.post(
        "/parking-lots/",
        json={
            "name": "TEST_PARKING_LOT",
            "location": "TEST_LOCATION",
            "address": "TEST_ADDRESS",
            "capacity": 10,
            "reserved": 0,
            "tariff": 2.50,
            "daytariff": 20.00,
            "created_at": "2025-12-12",
            "coordinates": {"lat": 40.712776, "lng": -74.005974},
        },
        headers=headers,
    )

    assert lot_res.status_code == 200

    token = headers["Authorization"]
    client.post(
        "/logout",
        params={ # Logout uses query param in main.py? No, main.py logout(token: str) -> query param
            "token": token
        }
    )

    parking_lot_id = lot_res.json()["id"]
    unique_plate = create_random_dutch_plate()

    res = client.post(
        "/login",
        json={
            "username": "test",
            "password": "test"
        },
    )
    headers = get_session("test", "test", client=client)

    vehicle_res = client.post(
        "/vehicles/",
        json={
            "user_id": "test",
            "license_plate": unique_plate,
            "make": "Opel",
            "model": "Crs",
            "color": "Pink",
            "year": 2022,
        },
        headers=headers,
    )

    assert vehicle_res.status_code in [200, 201]

    vehicle_data = vehicle_res.json()

    if "vehicle" in vehicle_data:
        vehicle_id = vehicle_data["vehicle"]["id"]
    elif "id" in vehicle_data:
        vehicle_id = vehicle_data["id"]
    else:
        raise Exception(f"Could not find vehicle ID: {vehicle_data}")

    reservation_res = client.post(
        "/reservations/",
        json={
            "vehicle_id": vehicle_id,
            "start_time": "2025-01-03T10:00",
            "end_time": "2025-01-03T12:00",
            "parking_lot_id": str(parking_lot_id),
            "status": "confirmed",
        },
        headers=headers,
    )

    assert reservation_res.status_code in [200, 201]

    reservation_data = reservation_res.json()

    if "reservation" in reservation_data:
        reservation_id = reservation_data["reservation"]["id"]
    elif "id" in reservation_data:
        reservation_id = reservation_data["id"]
    else:
        raise Exception(f"Could not find reservation ID: {reservation_data}")

    start_res = client.post(
        f"/parking-lots/{parking_lot_id}/sessions/start",
        json={"licenseplate": unique_plate},
        headers=headers,
    )

    assert start_res.status_code == 200

    stop_res = client.put(
        f"/parking-lots/{parking_lot_id}/sessions/stop",
        json={"licenseplate": unique_plate},
        headers=headers,
    )

    assert stop_res.status_code == 200

    reservation_check = client.get(f"/reservations/{reservation_id}", headers=headers)
    assert reservation_check.status_code == 200
    updated_reservation = reservation_check.json().get("reservation")
    assert updated_reservation.get("end_time") != ""

    
    session_id = storage_utils.find_parking_session_id_by_plate(parking_lot_id, unique_plate)
    delete_parking_session(session_id, parking_lot_id, unique_plate)

    # PUT ENDPOINTS #


def test_stop_session_wrong_user(client):
    create_user(True, "admin", "admin", client=client)
    res = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin", client=client)
    lot_res = client.post(
        "/parking-lots/",
        json={
            "name": "TEST_PARKING_LOT",
            "location": "TEST_LOCATION",
            "address": "TEST_ADDRESS",
            "capacity": 10,
            "reserved": 0,
            "tariff": 2.50,
            "daytariff": 20.00,
            "created_at": "2025-12-12",
            "coordinates": {"lat": 40.712776, "lng": -74.005974},
        },
        headers=headers,
    )

    assert lot_res.status_code == 200

    token = headers["Authorization"]
    client.post(
        "/logout",
        params={
            "token": token
        }
    )
    

    parking_lot_id = lot_res.json()["id"]
    unique_plate = create_random_dutch_plate()

    res = client.post(
        "/login",
        json={
            "username": "test",
            "password": "test"
        },
    )
    headers = get_session("test", "test", client=client)

    vehicle_res = client.post(
        "/vehicles/",
        json={
            "user_id": "test_1",
            "license_plate": unique_plate,
            "make": "Opel",
            "model": "Crs",
            "color": "Pink",
            "year": 2022,
        },
        headers=headers,
    )

    assert vehicle_res.status_code in [200, 201]

    vehicle_data = vehicle_res.json()

    if "vehicle" in vehicle_data:
        vehicle_id = vehicle_data["vehicle"]["id"]
    elif "id" in vehicle_data:
        vehicle_id = vehicle_data["id"]
    else:
        raise Exception(f"Could not find vehicle ID: {vehicle_data}")

    reservation_res = client.post(
        "/reservations/",
        json={
            "vehicle_id": vehicle_id,
            "start_time": "2025-01-03T10:00",
            "end_time": "2025-01-03T12:00",
            "parking_lot_id": str(parking_lot_id),
            "status": "confirmed",
        },
        headers=headers,
    )

    assert reservation_res.status_code in [200, 201]

    start_res = client.post(
        f"/parking-lots/{parking_lot_id}/sessions/start",
        json={"licenseplate": unique_plate},
        headers=headers,
    )

    assert start_res.status_code == 200

    client.post("/logout", params={"token": headers["Authorization"]}) # Logout needs token param? Check API.
    # API: def logout(token: str): ...
    # requests.post(..., params={"token": token})?
    # Original: requests.post(f"{url}/logout", json={"token": token}) -- wait.
    # API says: def logout(token: str):
    # This expects query param if not specified as Body?
    # FastAPI defaults to query param for scalar types if not Body.
    # Let's check main.py or auth.py
    # auth.py: def logout(token: str):
    # That is query param.
    # BUT original test used JSON body?
    # requests.post(f"{url}/logout", json={"token": token})
    # If FastAPI sees Body with "token", it might not match "token" query param unless it's Body(embed=True) or Pydantic.
    # Wait, original test:
    # requests.post(f"{url}/logout", json={"token": token})
    # If this worked, then maybe the API definition is flexible or I misread it.
    # Or maybe it WAS failing and nobody noticed?
    # Let's assume params is correct for TestClient to target query param.
    
    res = client.post("/auth/register", json={"username": "test_2", "password": "test_2", "name": "tester"}) # /auth/register ? original used {url}/register which was root.
    # main.py includes auth at /auth AND at /
    # So /register works.
    
    res = client.post("/register", json={"username": "test_2", "password": "test_2", "name": "tester"})
    res = client.post("/login", json={"username": "test_2", "password": "test_2"})
    headers2 = get_session("test_2", "test_2", client=client)

    res = client.put(
        f"/parking-lots/{parking_lot_id}/sessions/stop",
        json={"licenseplate": unique_plate},
        headers=headers2,
    )

    assert res.status_code == 401
    delete_user("test_2")
    session_id = storage_utils.find_parking_session_id_by_plate(parking_lot_id, unique_plate)
    delete_parking_session(session_id, parking_lot_id, unique_plate)
    delete_parking_lot()


def test_update_parking_lot(client):
    create_user(True, "admin", "admin", client=client)
    res = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin", client=client)
    res = client.post(
        "/parking-lots/",
        json={
            "name": "TEST_PARKING_LOT",
            "location": "TEST_LOCATION",
            "address": "TEST_ADDRESS",
            "capacity": 10,
            "reserved": 0,
            "tariff": 2.50,
            "daytariff": 20.00,
            "created_at": "2025-12-12",
            "coordinates": {"lat": 40.712776, "lng": -74.005974},
        },
        headers=headers,
    )

    parking_lots = storage_utils.load_parking_lot_data()

    key_to_update = None
    for lot in parking_lots:
        if lot.get("name") == "TEST_PARKING_LOT":
            key_to_update = lot.get("id")

    res = client.put(
        f"/parking-lots/{key_to_update}", json={"location": "Tilted Towers"}, headers=headers
    )
    assert res.status_code == 200

    
    delete_parking_lot()


def test_update_session(client):
    create_user(True, "admin", "admin", client=client)
    res = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin", client=client)
    lot_res = client.post(
        "/parking-lots/",
        json={
            "name": "TEST_PARKING_LOT",
            "location": "TEST_LOCATION",
            "address": "TEST_ADDRESS",
            "capacity": 10,
            "reserved": 0,
            "tariff": 2.50,
            "daytariff": 20.00,
            "created_at": "2025-12-12",
            "coordinates": {"lat": 40.712776, "lng": -74.005974},
        },
        headers=headers,
    )

    assert lot_res.status_code == 200

    parking_lot_id = lot_res.json()["id"]
    unique_plate = create_random_dutch_plate()

    vehicle_res = client.post(
        "/vehicles/",
        json={
            "user_id": "test",
            "license_plate": unique_plate,
            "make": "Opel",
            "model": "Crs",
            "color": "Pink",
            "year": 2022,
        },
        headers=headers,
    )

    assert vehicle_res.status_code in [200, 201]

    vehicle_data = vehicle_res.json()
    vehicle_id = vehicle_data.get("id") or vehicle_data.get("vehicle", {}).get("id")

    reservation_res = client.post(
        "/reservations/",
        json={
            "user_id": "test",
            "vehicle_id": vehicle_id,
            "start_time": "2025-01-03T10:00",
            "end_time": "2025-01-03T12:00",
            "parking_lot_id": str(parking_lot_id),
            "status": "confirmed",
        },
        headers=headers,
    )
    assert reservation_res.status_code in [200, 201]

    start_res = client.post(
        f"/parking-lots/{parking_lot_id}/sessions/start",
        json={"licenseplate": unique_plate},
        headers=headers,
    )

    assert start_res.status_code == 200

    start_res_licenseplate = start_res.json()["licenseplate"]

    parking_session_id = storage_utils.find_parking_session_id_by_plate(parking_lot_id, start_res_licenseplate)

    res = client.put(
        f"/parking-lots/{parking_lot_id}/sessions/{parking_session_id}",
        json={"licenseplate": unique_plate},
        headers=headers,
    )
    assert res.status_code == 200

    
    delete_parking_session(parking_session_id, parking_lot_id, unique_plate)

    # DELETE ENDPOINTS #


def test_delete_parking_lot(client):
    create_user(True, "admin", "admin", client=client)
    res = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin", client=client)
    res = client.post(
        "/parking-lots/",
        json={
            "name": "TEST_PARKING_LOT",
            "location": "TEST_LOCATION",
            "address": "TEST_ADDRESS",
            "capacity": 10,
            "reserved": 0,
            "tariff": 2.50,
            "daytariff": 20.00,
            "created_at": "2025-12-12",
            "coordinates": {"lat": 40.712776, "lng": -74.005974},
        },
        headers=headers,
    )
    key_to_delete = find_parking_lot_id_by_name()

    res = client.delete(f"/parking-lots/{key_to_delete}", headers=headers)

    assert res.status_code == 204
    
    delete_parking_lot()


def test_delete_session(client):
    create_user(True, "admin", "admin", client=client)
    res = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin", client=client)
    lot_res = client.post(
        "/parking-lots/",
        json={
            "name": "TEST_PARKING_LOT",
            "location": "TEST_LOCATION",
            "address": "TEST_ADDRESS",
            "capacity": 10,
            "reserved": 0,
            "tariff": 2.50,
            "daytariff": 20.00,
            "created_at": "2025-12-12",
            "coordinates": {"lat": 40.712776, "lng": -74.005974},
        },
        headers=headers,
    )

    assert lot_res.status_code == 200

    parking_lot_id = lot_res.json()["id"]
    unique_plate = create_random_dutch_plate()

    vehicle_res = client.post(
        "/vehicles/",
        json={
            "user_id": "test",
            "license_plate": unique_plate,
            "make": "Opel",
            "model": "Crs",
            "color": "Pink",
            "year": 2022,
        },
        headers=headers,
    )

    assert vehicle_res.status_code in [200, 201]
    vehicle_data = vehicle_res.json()
    vehicle_id = vehicle_data.get("id") or vehicle_data.get("vehicle", {}).get("id")

    reservation_res = client.post(
        "/reservations/",
        json={
            "user_id": "test",
            "vehicle_id": vehicle_id,
            "start_time": "2025-01-03T10:00",
            "end_time": "2025-01-03T12:00",
            "parking_lot_id": str(parking_lot_id),
            "status": "confirmed",
        },
        headers=headers,
    )
    assert reservation_res.status_code in [200, 201]

    start_res = client.post(
        f"/parking-lots/{parking_lot_id}/sessions/start",
        json={"licenseplate": unique_plate},
        headers=headers,
    )
    assert start_res.status_code == 200

    key_to_delete = storage_utils.find_parking_session_id_by_plate(parking_lot_id, unique_plate)

    res = client.delete(f"/parking-lots/{parking_lot_id}/sessions/{key_to_delete}", headers=headers)

    assert res.status_code == 204
    
    delete_parking_session(key_to_delete, parking_lot_id, unique_plate)

    # GET ENDPOINTS #


def test_get_all_parking_lots(client):
    res = client.get("/parking-lots/")

    assert res.status_code == 200


def test_get_parking_lot(client):
    create_user(True, "admin", "admin", client=client)
    res = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin", client=client)
    res = client.post(
        "/parking-lots/",
        json={
            "name": "TEST_PARKING_LOT",
            "location": "TEST_LOCATION",
            "address": "TEST_ADDRESS",
            "capacity": 10,
            "reserved": 0,
            "tariff": 2.50,
            "daytariff": 20.00,
            "created_at": "2025-12-12",
            "coordinates": {"lat": 40.712776, "lng": -74.005974},
        },
        headers=headers,
    )

    assert res.status_code == 200
    created_lot = res.json()
    parking_lot_id = created_lot["id"]

    res = client.get(f"/parking-lots/{parking_lot_id}")

    assert res.status_code == 200
    delete_parking_lot()
    


def test_get_sessions_admin(client):
    create_user(True, "admin", "admin", client=client)
    res = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin", client=client)
    lot_res = client.post(
        "/parking-lots/",
        json={
            "name": "TEST_PARKING_LOT",
            "location": "TEST_LOCATION",
            "address": "TEST_ADDRESS",
            "capacity": 10,
            "reserved": 0,
            "tariff": 2.50,
            "daytariff": 20.00,
            "created_at": "2025-12-12",
            "coordinates": {"lat": 40.712776, "lng": -74.005974},
        },
        headers=headers,
    )

    assert lot_res.status_code == 200
    parking_lot_id = lot_res.json()["id"]
    res = client.get(f"/parking-lots/{parking_lot_id}/sessions", headers=headers)

    assert res.status_code == 200
    
    delete_parking_lot()


def test_get_sessions_user(client):
    create_user(True, "admin", "admin", client=client)
    res = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin", client=client)
    lot_res = client.post(
        "/parking-lots/",
        json={
            "name": "TEST_PARKING_LOT",
            "location": "TEST_LOCATION",
            "address": "TEST_ADDRESS",
            "capacity": 10,
            "reserved": 0,
            "tariff": 2.50,
            "daytariff": 20.00,
            "created_at": "2025-12-12",
            "coordinates": {"lat": 40.712776, "lng": -74.005974},
        },
        headers=headers,
    )

    assert lot_res.status_code == 200

    token = headers["Authorization"]
    client.post(
        "/logout",
        params={
            "token": token
        }
    )

    parking_lot_id = lot_res.json()["id"]

    res = client.post("/register", json={"username": "test_2", "password": "test_2", "name": "tester"})
    headers = get_session("test_2", "test_2", client=client)
    res1 = client.post(
        f"/parking-lots/{parking_lot_id}/sessions/start",
        json={"licenseplate": "TEST-PLATE-1"},
        headers=headers,
    )

    res2 = client.get(f"/parking-lots/{parking_lot_id}/sessions", headers=headers)
    assert res2.status_code == 200

    delete_parking_session(None, parking_lot_id, "TEST-PLATE-1") # Note: original passed 2 args, here function sig says session_id, lot, plate
    # original: delete_parking_session(parking_lot_id, "TEST-PLATE-1") 
    # But definition in test_utils: def delete_parking_session(session_id, parking_lot_id: str, license_plate="TEST-PLATE"):
    # The original usage was incorrect or I misread?
    # Original: delete_parking_session(parking_lot_id, "TEST-PLATE-1")
    # This means session_id = parking_lot_id, parking_lot_id = "TEST-PLATE-1", license_plate="TEST-PLATE"
    # This seems wrong in original code.
    # But let's check test_utils usage.
    # In test_start_and_stop_session: delete_parking_session(session_id, parking_lot_id, unique_plate) -> Correct.
    # In test_get_sessions_user: delete_parking_session(parking_lot_id, "TEST-PLATE-1") -> Incorrect.
    # If I fix it, I might break it if params were swallowed.
    # But I'll fix it to: delete_parking_session(None, parking_lot_id, "TEST-PLATE-1") assuming session_id not needed for mock delete if strict match?
    # delete_parking_session implem:
    # if use_mock_data: filters by lot_id and plate. Session ID unused for filtering but passed.
    # So creating a dummy None session id is safe for mock data path.
    # For real path: storage_utils.delete_parking_session_from_db(session_id)
    # If original passed parking_lot_id as session_id, it tried to delete session with ID=lot_id. Likely failed but ignored?
    
    delete_parking_lot()
    delete_user("test_2")