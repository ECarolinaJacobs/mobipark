import requests
import json
import os
import random
from utils import storage_utils
from dotenv import find_dotenv

find_dotenv()

url = "http://localhost:8000/"

def create_user(isAdmin, username="test", password="test"):
    # Ensure clean slate
    delete_user(username)
    
    requests.post(f"{url}/register", json={"username": username, "password": password, "name": "tester"})

    if isAdmin:
        update_user_role(username, "ADMIN")
    else:
        update_user_role(username, "USER")

def delete_user(username="test"):
    users = storage_utils.load_user_data()
    new_users = [u for u in users if u["username"] != username]
    storage_utils.save_user_data(new_users)

def update_user_role(username, role):
    users = storage_utils.load_user_data()
    for user in users:
        if user["username"] == username:
            user["role"] = role
    storage_utils.save_user_data(users)

def delete_parking_lot(name="TEST_PARKING_LOT"):
    parking_lots = storage_utils.load_parking_lot_data()
    new_parking_lots = {k: v for k, v in parking_lots.items() if v.get("name") != name}
    storage_utils.save_parking_lot_data(new_parking_lots)

def delete_parking_session(parking_lot_id: str, license_plate="TEST-PLATE"):
    sessions = storage_utils.load_parking_session_data(parking_lot_id)
    new_parking_sessions = {k: v for k, v in sessions.items() if v.get("licenseplate") != license_plate}
    storage_utils.save_parking_session_data(new_parking_sessions, parking_lot_id)

def find_parking_lot_id_by_name():
    parking_lots = storage_utils.load_parking_lot_data()
    for k, v in parking_lots.items():
        if v.get("name") == "TEST_PARKING_LOT":
            return k
        
def find_parking_session_id_by_plate(parking_lot_id: str, licenseplate: str):
    sessions = storage_utils.load_parking_session_data(parking_lot_id)
    for k, v in sessions.items():
        if v.get("licenseplate") == licenseplate:
            return k

def get_session(username="test", password="test"):
    res = requests.post(f"{url}/login", json={"username": username, "password": password})
    try:
        ses_token = res.json()["session_token"]
        return {"Authorization": ses_token}
    except KeyError:
        # Fallback or error handling if login fails
        raise Exception(f"Login failed for {username}: {res.text}")

def create_random_dutch_plate():
    patterns = [
        lambda: f"{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}-{random.randint(10, 99)}-{random.randint(10, 99)}", 
        lambda: f"{random.randint(10, 99)}-{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}-{random.randint(10, 99)}",  
        lambda: f"{random.randint(10, 99)}-{random.randint(10, 99)}-{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}",
        lambda: f"{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}-{random.randint(10, 99)}-{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}",
        lambda: f"{random.randint(10, 99)}-{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}-{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}",
        lambda: f"{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}-{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}-{random.randint(10, 99)}",
    ]
    return random.choice(patterns)()