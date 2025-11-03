import requests
import json

url = "http://localhost:8000/"

def create_user(username="test", password="test"):
    requests.post(f"{url}/register", json={"username": username, "password": password, "name": "tester"})
    update_user_role(username)

def delete_user(username="test"):
    filename = "../data/users.json"
    with open(filename, "r") as f:
        users = json.load(f)
    
    new_users = [u for u in users if u["username"] != username]
    with open(filename, "w") as f:
        json.dump(new_users, f)

def update_user_role(username):
    filename = "../data/users.json"
    with open (filename, "r") as f:
        users = json.load(f)
    for user in users:
        if user["username"] == username:
            user["role"] = "ADMIN"
    with open(filename, "w") as f:
        json.dump(users, f)

def delete_parking_lot(name="TEST_PARKING_LOT"):
    filename = "../data/parking-lots.json"
    with open(filename, "r") as f:
        parking_lots = json.load(f)
    
    new_parking_lots = {k: v for k, v in parking_lots.items() if v.get("name") != name}

    with open(filename, "w") as f:
        json.dump(new_parking_lots, f)

def find_parking_lot_id_by_name():
    filename = "../data/parking-lots.json"
    with open(filename, "r") as f:
        parking_lots = json.load(f)

    key_to_update = None
    for k, v in parking_lots.items():
        if v.get("name") == "TEST_PARKING_LOT":
            return k

def get_session(username="test", password="test"):
    res = requests.post(f"{url}/login", json={"username": username, "password": password})
    ses_token = res.json()["session_token"]
    return {"Authorization": ses_token}
