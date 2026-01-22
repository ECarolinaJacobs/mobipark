import pytest
import requests
import json
from test.test_utils import (
    create_user,
    delete_user,
    get_session,
    delete_parking_lot,
    find_parking_lot_id_by_name,
    find_parking_session_id_by_plate,
    delete_parking_session,
    url,
    create_random_dutch_plate,
    load_parking_lots_from_mock,
    update_user_role
)
from utils import storage_utils

# TODO: TEST EDGE CASES

# POST ENDPOINTS #

# def test_create_users():
#     res2 = requests.post(f"{url}/register", json={"username": "admin", "password": "admin", "name": "admin"})
#     update_user_role("admin", "ADMIN")
#     assert res2.status_code == 200

#     res = requests.post(f"{url}/register", json={"username": "test", "password": "test", "name": "tester"})
#     assert res.status_code == 200


def test_create_parking_lot():
    # create_user(True)
    res = requests.post(
        f"{url}/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin")
    
    res = requests.post(
        f"{url}/parking-lots/",
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


def test_start_and_stop_session():
    delete_parking_lot()
    # create_user(True, "test_admin", "test")
    res = requests.post(
        f"{url}/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin")
    lot_res = requests.post(
        f"{url}/parking-lots/",
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
    requests.post(
        f"{url}/logout",
        json={
            "token": token
        }
    )

    parking_lot_id = lot_res.json()["id"]
    unique_plate = create_random_dutch_plate()

    res = requests.post(
        f"{url}/login",
        json={
            "username": "test",
            "password": "test"
        },
    )
    headers = get_session("test", "test")

    vehicle_res = requests.post(
        f"{url}/vehicles/",
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

    reservation_res = requests.post(
        f"{url}/reservations/",
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

    start_res = requests.post(
        f"{url}/parking-lots/{parking_lot_id}/sessions/start",
        json={"licenseplate": unique_plate},
        headers=headers,
    )

    assert start_res.status_code == 200

    stop_res = requests.put(
        f"{url}/parking-lots/{parking_lot_id}/sessions/stop",
        json={"licenseplate": unique_plate},
        headers=headers,
    )

    assert stop_res.status_code == 200

    reservation_check = requests.get(f"{url}/reservations/{reservation_id}", headers=headers)
    assert reservation_check.status_code == 200
    updated_reservation = reservation_check.json().get("reservation")
    assert updated_reservation.get("end_time") != ""

    
    session_id = storage_utils.find_parking_session_id_by_plate(parking_lot_id, unique_plate)
    delete_parking_session(session_id, parking_lot_id, unique_plate)

    # PUT ENDPOINTS #


def test_stop_session_wrong_user():
    res = requests.post(
        f"{url}/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin")
    lot_res = requests.post(
        f"{url}/parking-lots/",
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
    requests.post(
        f"{url}/logout",
        json={
            "token": token
        }
    )
    

    parking_lot_id = lot_res.json()["id"]
    unique_plate = create_random_dutch_plate()

    res = requests.post(
        f"{url}/login",
        json={
            "username": "test",
            "password": "test"
        },
    )
    headers = get_session("test", "test")

    vehicle_res = requests.post(
        f"{url}/vehicles/",
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

    reservation_res = requests.post(
        f"{url}/reservations/",
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

    start_res = requests.post(
        f"{url}/parking-lots/{parking_lot_id}/sessions/start",
        json={"licenseplate": unique_plate},
        headers=headers,
    )

    assert start_res.status_code == 200

    requests.post(f"{url}/logout", headers=headers)
    res = requests.post(f"{url}/register", json={"username": "test_2", "password": "test_2", "name": "tester"})
    res = requests.post(f"{url}/login", json={"username": "test_2", "password": "test_2"})
    headers2 = get_session(username="test_2", password="test_2")

    res = requests.put(
        f"{url}/parking-lots/{parking_lot_id}/sessions/stop",
        json={"licenseplate": unique_plate},
        headers=headers2,
    )

    assert res.status_code == 401
    delete_user("test_2")
    session_id = storage_utils.find_parking_session_id_by_plate(parking_lot_id, unique_plate)
    delete_parking_session(session_id, parking_lot_id, unique_plate)
    delete_parking_lot()


def test_update_parking_lot():
    res = requests.post(
        f"{url}/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin")
    res = requests.post(
        f"{url}/parking-lots/",
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

    res = requests.put(
        f"{url}/parking-lots/{key_to_update}", json={"location": "Tilted Towers"}, headers=headers
    )
    assert res.status_code == 200

    
    delete_parking_lot()


def test_update_session():
    res = requests.post(
        f"{url}/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin")
    lot_res = requests.post(
        f"{url}/parking-lots/",
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

    vehicle_res = requests.post(
        f"{url}/vehicles/",
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

    reservation_res = requests.post(
        f"{url}/reservations/",
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

    start_res = requests.post(
        f"{url}/parking-lots/{parking_lot_id}/sessions/start",
        json={"licenseplate": unique_plate},
        headers=headers,
    )

    assert start_res.status_code == 200

    start_res_licenseplate = start_res.json()["licenseplate"]

    parking_session_id = storage_utils.find_parking_session_id_by_plate(parking_lot_id, start_res_licenseplate)

    res = requests.put(
        f"{url}/parking-lots/{parking_lot_id}/sessions/{parking_session_id}",
        json={"licenseplate": unique_plate},
        headers=headers,
    )
    assert res.status_code == 200

    
    delete_parking_session(parking_session_id, parking_lot_id, unique_plate)

    # DELETE ENDPOINTS #


def test_delete_parking_lot():
    res = requests.post(
        f"{url}/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin")
    res = requests.post(
        f"{url}/parking-lots/",
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

    res = requests.delete(f"{url}/parking-lots/{key_to_delete}", headers=headers)

    assert res.status_code == 204
    
    delete_parking_lot()


def test_delete_session():
    res = requests.post(
        f"{url}/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin")
    lot_res = requests.post(
        f"{url}/parking-lots/",
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

    vehicle_res = requests.post(
        f"{url}/vehicles/",
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

    reservation_res = requests.post(
        f"{url}/reservations/",
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

    start_res = requests.post(
        f"{url}/parking-lots/{parking_lot_id}/sessions/start",
        json={"licenseplate": unique_plate},
        headers=headers,
    )
    assert start_res.status_code == 200

    key_to_delete = storage_utils.find_parking_session_id_by_plate(parking_lot_id, unique_plate)

    res = requests.delete(f"{url}/parking-lots/{parking_lot_id}/sessions/{key_to_delete}", headers=headers)

    assert res.status_code == 204
    
    delete_parking_session(key_to_delete, parking_lot_id, unique_plate)

    # GET ENDPOINTS #


def test_get_all_parking_lots():
    res = requests.get(f"{url}/parking-lots/")

    assert res.status_code == 200


def test_get_parking_lot():
    res = requests.post(
        f"{url}/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin")
    res = requests.post(
        f"{url}/parking-lots/",
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

    res = requests.get(f"{url}/parking-lots/{parking_lot_id}")

    assert res.status_code == 200
    delete_parking_lot()
    


def test_get_sessions_admin():
    res = requests.post(
        f"{url}/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin")
    lot_res = requests.post(
        f"{url}/parking-lots/",
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
    res = requests.get(f"{url}/parking-lots/{parking_lot_id}/sessions", headers=headers)

    assert res.status_code == 200
    
    delete_parking_lot()


def test_get_sessions_user():
    res = requests.post(
        f"{url}/login",
        json={
            "username": "admin",
            "password": "admin"
        },
    )
    headers = get_session("admin", "admin")
    lot_res = requests.post(
        f"{url}/parking-lots/",
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
    requests.post(
        f"{url}/logout",
        json={
            "token": token
        }
    )

    parking_lot_id = lot_res.json()["id"]

    res = requests.post(f"{url}/register", json={"username": "test_2", "password": "test_2", "name": "tester"})
    headers = get_session("test_2", "test_2")
    res1 = requests.post(
        f"{url}/parking-lots/{parking_lot_id}/sessions/start",
        json={"licenseplate": "TEST-PLATE-1"},
        headers=headers,
    )

    res2 = requests.get(f"{url}/parking-lots/{parking_lot_id}/sessions", headers=headers)
    assert res2.status_code == 200

    delete_parking_session(parking_lot_id, "TEST-PLATE-1")
    delete_parking_lot()
    delete_user("test_2")
