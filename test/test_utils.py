import requests
import json
import os
from utils import storage_utils
from dotenv import find_dotenv

find_dotenv()
use_mock_data = os.getenv("USE_MOCK_DATA", "true") == "true"

url = "http://localhost:8000/"

def create_user(isAdmin, username="test", password="test"):
    requests.post(f"{url}/register", json={"username": username, "password": password, "name": "tester"})

    if isAdmin:
        update_user_role(username, "ADMIN")
    else:
        update_user_role(username, "USER")

def delete_user(username="test"):
    filename = "../data/users.json"
    if use_mock_data:
        filename = "../mock_data/mock_users.json"
    with open(filename, "r") as f:
        users = json.load(f)
    
    new_users = [u for u in users if u["username"] != username]
    with open(filename, "w") as f:
        json.dump(new_users, f)

def update_user_role(username, role):
    filename = "../data/users.json"
    if use_mock_data:
        filename = "../mock_data/mock_users.json"
    with open (filename, "r") as f:
        users = json.load(f)
    for user in users:
        if user["username"] == username:
            user["role"] = role
    with open(filename, "w") as f:
        json.dump(users, f)

def delete_parking_lot(name="TEST_PARKING_LOT"):
    filename = "../data/parking-lots.json"
    if use_mock_data:
        filename = "../mock_data/mock_parking-lots.json"
    with open(filename, "r") as f:
        parking_lots = json.load(f)
    
    new_parking_lots = {k: v for k, v in parking_lots.items() if v.get("name") != name}

    with open(filename, "w") as f:
        json.dump(new_parking_lots, f)

def delete_parking_session(parking_lot_id: str, license_plate="TEST-PLATE"):
    filename = f"../data/pdata/p{parking_lot_id}-sessions.json"
    with open(filename, "r") as f:
        sessions = json.load(f)
    new_parking_sessions = {k: v for k, v in sessions.items() if v.get("licenseplate") != license_plate}
    with open(filename, "w") as f:
        json.dump(new_parking_sessions, f)

def find_parking_lot_id_by_name():
    filename = "../data/parking-lots.json"
    if use_mock_data:
        filename = "../mock_data/mock_parking-lots.json"
    with open(filename, "r") as f:
        parking_lots = json.load(f)

    for k, v in parking_lots.items():
        if v.get("name") == "TEST_PARKING_LOT":
            return k
        
def find_parking_session_id_by_plate(parking_lot_id: str):
    filename = f"../data/pdata/p{parking_lot_id}-sessions.json"
    with open(filename, "r") as f:
        parking_lots = json.load(f)

    for k, v in parking_lots.items():
        if v.get("licenseplate") == "TEST-PLATE":
            return k

def get_session(username="test", password="test"):
    res = requests.post(f"{url}/login", json={"username": username, "password": password})
    ses_token = res.json()["session_token"]
    return {"Authorization": ses_token}
