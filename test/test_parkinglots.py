import pytest
import requests
import json
from utils import create_user, delete_user, update_user_role, get_session, delete_parking_lot, find_parking_lot_id_by_name, url

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
        "coordinates": {
            "latitude": 40.712776,
            "longitude": -74.005974
        }}, 
    headers=headers)

    assert res.status_code == 201
    delete_user()
    delete_parking_lot()

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
        "coordinates": {
            "latitude": 40.712776,
            "longitude": -74.005974
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
        "coordinates": {
            "latitude": 40.712776,
            "longitude": -74.005974
        }}, 
    headers=headers)
    key_to_delete = find_parking_lot_id_by_name()

    res = requests.delete(f"{url}/parking-lots/{key_to_delete}", headers=headers)

    assert res.status_code == 200
    delete_user()
    delete_parking_lot()

def test_get_parking_lot():
    parking_lot_id = 1
    res = requests.get(f"{url}/parking-lots/{parking_lot_id}")
    
    assert res.status_code == 200