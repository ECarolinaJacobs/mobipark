import pytest
import requests
import json
from test.test_utils import create_user, delete_user, update_user_role, get_session, delete_parking_lot, find_parking_lot_id_by_name, url

    # POST ENDPOINTS #

def test_create_parking_lot():
    create_user()
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
    create_user()
    headers = get_session()
    parking_lot_id = 1
    res = requests.post(f"{url}/parking-lots/sessions/{1}/start", json={
        "licenseplate": "TEST-PLATE"
    },
    headers=headers)

    assert res.status_code == 200

    res = requests.put(f"{url}/parking-lots/sessions/{1}/stop", json={
        "licenseplate": "TEST-PLATE"
    },
    headers=headers)

    assert res.status_code == 200
    delete_user()

def test_stop_session_wrong_user():
    pass

    # PUT ENDPOINTS #

def test_update_parking_lot():
    create_user()
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
    
    res = requests.put(f"{url}/parking-lots/{key_to_update}", json={"name": "TEST_PARKING_LOT_UPDATED"}, headers=headers)
    assert res.status_code == 200

    delete_user()
    delete_parking_lot()

def test_update_session():
    pass

    # DELETE ENDPOINTS #

def test_delete_parking_lot():
    create_user()
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
            "latitude": 40.712776,
            "longitude": -74.005974
        }}, 
    headers=headers)
    key_to_delete = find_parking_lot_id_by_name()

    res = requests.delete(f"{url}/parking-lots/{key_to_delete}", headers=headers)

    assert res.status_code == 204
    delete_user()
    delete_parking_lot()

def test_delete_sessions():
    pass

    # GET ENDPOINTS #

def test_get_all_parking_lots():
    res = requests.get(f"{url}/parking-lots/")

    assert res.status_code == 200

def test_get_parking_lot():
    parking_lot_id = 1
    res = requests.get(f"{url}/parking-lots/{parking_lot_id}")
    
    assert res.status_code == 200

def test_get_sessions_admin():
    create_user()
    parking_lot_id = 1
    res = requests.get(f"{url}/parking-lots/{parking_lot_id}/sessions")

    assert res.status_code == 200
    delete_user()

def test_get_sessions_user():
    pass