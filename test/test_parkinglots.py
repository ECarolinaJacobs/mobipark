import pytest
import requests
import json
from test.test_utils import create_user, delete_user, get_session, delete_parking_lot, find_parking_lot_id_by_name, find_parking_session_id_by_plate, delete_parking_session, url

    # TODO: TEST EDGE CASES
    

    # POST ENDPOINTS #

def test_create_parking_lot():
    create_user(True)
    headers = get_session()
    res = requests.post(f"{url}/parking-lots/", json={
        "name": "TEST_PARKING_LOT",
        "location": "TEST_LOCATION",
        "address": "TEST_ADDRESS",
        "capacity": 10,
        "reserved": 0,
        "tariff": 2.50,
        "daytariff": 20.00,
        "created_at": "2025-12-12",
        "coordinates": {
            "lat": 40.712776,
            "lng": -74.005974
        }}, 
    headers=headers)

    assert res.status_code == 200
    delete_user()
    delete_parking_lot()

def test_start_and_stop_session():
    parking_lot_id = 1
    delete_parking_session(parking_lot_id)
    create_user(False)
    headers = get_session()
    res = requests.post(f"{url}/parking-lots/{parking_lot_id}/sessions/start", json={
        "licenseplate": "TEST-PLATE"
    },
    headers=headers)

    assert res.status_code == 200

    res = requests.put(f"{url}/parking-lots/{parking_lot_id}/sessions/stop", json={
        "licenseplate": "TEST-PLATE"
    },
    headers=headers)

    assert res.status_code == 200
    delete_user()
    delete_parking_session(parking_lot_id)

def test_stop_session_wrong_user():
    parking_lot_id = 1
    delete_parking_session(parking_lot_id)
    create_user(False, username="test_1", password="test_1")
    headers = get_session(username="test_1", password="test_1")
    requests.post(f"{url}/parking-lots/{parking_lot_id}/sessions/start", json={
        "licenseplate": "TEST-PLATE"
    },
    headers=headers)

    requests.post(f"{url}/logout", headers=headers)
    create_user(False, username="test_2", password="test_2")
    headers2 = get_session(username="test_2", password="test_2")

    res = requests.put(f"{url}/parking-lots/{parking_lot_id}/sessions/stop", json={
        "licenseplate": "TEST-PLATE"
    },
    headers=headers2)

    assert res.status_code == 401
    delete_user("test_1")
    delete_user("test_2")
    delete_parking_session(parking_lot_id)

    # PUT ENDPOINTS #

def test_update_parking_lot():
    create_user(True)
    headers = get_session() 
    res = requests.post(f"{url}/parking-lots/", json={
        "name": "TEST_PARKING_LOT",
        "location": "TEST_LOCATION",
        "address": "TEST_ADDRESS",
        "capacity": 10,
        "reserved": 0,
        "tariff": 2.50,
        "daytariff": 20.00,
        "created_at": "2025-12-12",
        "coordinates": {
            "lat": 40.712776,
            "lng": -74.005974
        }}, 
    headers=headers)

    filename = "../data/parking-lots.json"
    with open(filename, "r") as f:
        parking_lots = json.load(f)

    key_to_update = None
    for k, v in parking_lots.items():
        if v.get("name") == "TEST_PARKING_LOT":
            key_to_update = k
    
    res = requests.put(f"{url}/parking-lots/{key_to_update}", json={
        "location": "Tilted Towers"},
        headers=headers)
    assert res.status_code == 200

    delete_user()
    delete_parking_lot()

def test_update_session():
    pass

    # DELETE ENDPOINTS #

def test_delete_parking_lot():
    create_user(True)
    headers = get_session()
    res = requests.post(f"{url}/parking-lots/", json={
        "name": "TEST_PARKING_LOT",
        "location": "TEST_LOCATION",
        "address": "TEST_ADDRESS",
        "capacity": 10,
        "reserved": 0,
        "tariff": 2.50,
        "daytariff": 20.00,
        "created_at": "2025-12-12",
        "coordinates": {
            "lat": 40.712776,
            "lng": -74.005974
        }}, 
    headers=headers)
    key_to_delete = find_parking_lot_id_by_name()

    res = requests.delete(f"{url}/parking-lots/{key_to_delete}", headers=headers)

    assert res.status_code == 204
    delete_user()
    delete_parking_lot()

def test_delete_session():
    parking_lot_id = 1
    delete_parking_session(parking_lot_id)

    create_user(True)
    headers = get_session()

    requests.post(f"{url}/parking-lots/{parking_lot_id}/sessions/start", json={
        "licenseplate": "TEST-PLATE"
    },
    headers=headers)
    key_to_delete = find_parking_session_id_by_plate(parking_lot_id)

    res = requests.delete(f"{url}/parking-lots/{parking_lot_id}/sessions/{key_to_delete}", headers=headers)

    assert res.status_code == 204
    delete_user()
    delete_parking_session(parking_lot_id)

    # GET ENDPOINTS #

def test_get_all_parking_lots():
    res = requests.get(f"{url}/parking-lots/")

    assert res.status_code == 200

def test_get_parking_lot():
    parking_lot_id = 1
    res = requests.get(f"{url}/parking-lots/{parking_lot_id}")
    
    assert res.status_code == 200

def test_get_sessions_admin():
    create_user(True)
    headers = get_session()
    parking_lot_id = 1
    res = requests.get(f"{url}/parking-lots/{parking_lot_id}/sessions", headers=headers)

    assert res.status_code == 200
    delete_user()

def test_get_sessions_user():
    parking_lot_id = "1"
    delete_parking_session(parking_lot_id, "TEST-PLATE-1")

    create_user(False)
    headers = get_session()
    res1 = requests.post(f"{url}/parking-lots/{parking_lot_id}/sessions/start", json={
        "licenseplate": "TEST-PLATE-1"
    },
    headers=headers)

    res2 = requests.get(f"{url}/parking-lots/{parking_lot_id}/sessions", headers=headers)
    assert res2.status_code == 200

    delete_parking_session(parking_lot_id, "TEST-PLATE-1")
    delete_user("test_1")