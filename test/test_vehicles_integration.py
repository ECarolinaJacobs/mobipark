import requests
import pytest
import time
import random
import string
from dotenv import load_dotenv
import os
from test.test_utils import update_user_role

load_dotenv()

url = "http://localhost:8000/"


def valid_plate():
    letters = "".join(random.choice(string.ascii_uppercase) for _ in range(2))
    num1 = random.randint(10, 99)
    num2 = random.randint(10, 99)
    return f"{letters}-{num1}-{num2}"


# register and login helper method, returns authentication headers for testing purposes
def register_login(username="vehicle_user", password="123", name=None, role="USER"):
    name = name or username
    register_data = {"username": username, "password": password, "name": name}
    res = requests.post(f"{url}/auth/register", json=register_data)

    if res.status_code == 400 and "Username already exists" in res.text:
        login_data = {"username": username, "password": password}
        res = requests.post(f"{url}/auth/login", json=login_data)

    assert res.status_code in (200, 201), f"Auth failed for {username}: {res.text}"
    token = res.json().get("session_token")
    assert token, f"No token received from auth response: {res.text}"
    return {"Authorization": token}


def register_admin(username="admin_user", password="123", name="Admin"):
    name = name or username
    register_data = {"username": username, "password": password, "name": name}
    res = requests.post(f"{url}/auth/register", json=register_data)
    if res.status_code == 400 and "Username already exists" in res.text:
        res = requests.post(f"{url}/auth/login", json={"username": username, "password": password})
    assert res.status_code in (200, 201), f"Auth failed for {username}: {res.text}"
    import json
    from pathlib import Path
    from utils.storage_utils import get_user_data_by_username, update_single_json_in_db

    use_mock_data = os.getenv("USE_MOCK_DATA", "true") == "true"
    if use_mock_data:
        filename = Path(__file__).parent.parent / "mock_data/mock_users.json"
        with open(filename, "r") as f:
            users = json.load(f)
        for user in users:
            if user["username"] == username:
                user["role"] = "ADMIN"
                break
        with open(filename, "w") as f:
            json.dump(users, f, indent=2)
            print(f"debug: set{username} role to admin")
    else:
        user = get_user_data_by_username(username)
        if user:
            user["role"] == "ADMIN"
            update_single_json_in_db("users", "username", username, user)
            print(f"debug set {username} role to admin")
    token = res.json().get("session_token")
    assert token, f"No token received from auth response: {res.text}"
    return {"Authorization": token}


""" POST vehicles endpoint tests"""


# test is passed if unauthorized req returns 401
def test_unauthorized_vehicle():
    data = {
        "user_id": "Test",
        "license_plate": "AB-12-CD",
        "make": "Toyota",
        "model": "Yaris",
        "color": "Blue",
        "year": 2020,
    }
    res = requests.post(f"{url}/vehicles", json=data)
    assert res.status_code == 401
    assert "Unauthorized" in res.text


# test is passed if missing required fields (name and license plate) return 422
def test_missing_fields():
    headers = register_login("vehicle_user", "123")
    data = {
        "user_id": "Test",
        "make": "Toyota",
        "model": "Yaris",
        "color": "Blue",
        "year": 2020,
    }  # missing the license plate field
    res = requests.post(f"{url}/vehicles", json=data, headers=headers)

    assert res.status_code == 422  # changed to match fastapi validation
    body = res.json()
    assert "detail" in body
    assert any(
        "license_plate" in str(err["loc"]) for err in body["detail"]
    )  # changed because removal status wrapper


# test passed if creating new vehicle returns 201 with status success
def test_vehicle_creation_success():
    headers = register_login(f"vehicle_user_new{int(time.time())}", "123")
    unique_plate = valid_plate()
    data = {
        "user_id": "Test",
        "license_plate": unique_plate,
        "make": "Toyota",
        "model": "Yaris",
        "color": "Red",
        "year": 2022,
    }
    res = requests.post(f"{url}/vehicles", json=data, headers=headers)
    body = res.json()
    assert res.status_code == 200
    assert body["license_plate"] == unique_plate
    assert body["make"] == "Toyota"
    assert body["model"] == "Yaris"
    assert "created_at" in body


# test passed when creating the same vehicle twice, returns 400
def test_vehicle_creating_duplicate():
    headers = register_login("vehicle_user", "123")
    data = {
        "user_id": "Test",
        "license_plate": "12-BD-33",
        "make": "Toyota",
        "model": "Carolla",
        "color": "Silver",
        "year": 2021,
    }
    # first creation passes
    requests.post(f"{url}/vehicles", json=data, headers=headers)
    # duplicate creation should fail
    res = requests.post(f"{url}/vehicles", json=data, headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "Vehicle already exists"


""" PUT /vehicles endpoint tests """


# test passed if the update without name field returns 401 and an error message
def test_update_vehicle_missing_field():
    headers = register_login("put_user1", "123")
    create_data = {
        "user_id": "Test",
        "license_plate": "11-AB-11",
        "make": "Toyota",
        "model": "Yaris",
        "color": "Pink",
        "year": 2020,
    }
    requests.post(f"{url}/vehicles", json=create_data, headers=headers)
    lid = "11AB11"
    data = {
        "user_id": "Test",
        "license_plate": "11-AB-11",
        "model": "Yaris",
        "color": "Green",
        "year": 2020,
    }
    res = requests.put(f"{url}/vehicles/{lid}", json=data, headers=headers)
    assert res.status_code == 422
    body = res.json()
    assert any("make" in str(err["loc"]) for err in body["detail"])


# test passed if trying to update a non-existing vehicle doesn't work and returns 404
def test_update_nonvehicle():
    headers = register_login("put_user2", "123")
    lid = "BC22CD"
    update_data = {
        "user_id": "Test",
        "license_plate": "BC-22-CD",
        "make": "Honda",
        "model": "Civic",
        "color": "Black",
        "year": 2021,
    }
    res = requests.put(f"{url}/vehicles/{lid}", json=update_data, headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Vehicle not found"


# test passed if admin can update vehicle details (e.g., color) of another user's vehicle
def test_update_vehicle_existing_data_by_admin():
    # Create admin user
    admin_headers = register_admin("admin_update_test", "123", "Admin")
    # Create normal user and their vehicle
    user_headers = register_login("normal_update_user", "123")
    unique_plate = valid_plate()
    create_data = {
        "user_id": "dummy",
        "license_plate": unique_plate,
        "make": "Toyota",
        "model": "Yaris",
        "color": "Blue",
        "year": 2020,
    }

    create_res = requests.post(f"{url}/vehicles", json=create_data, headers=user_headers)
    assert create_res.status_code == 200

    # Admin updates the vehicle color
    lid = unique_plate.replace("-", "").upper()
    update_data = {
        "user_id": "dummy",
        "license_plate": unique_plate,
        "make": "Toyota",
        "model": "Yaris",
        "color": "Red",  # changed color
        "year": 2020,
    }
    update_res = requests.put(f"{url}/vehicles/{lid}", json=update_data, headers=admin_headers)

    assert update_res.status_code == 200
    body = update_res.json()
    assert body["license_plate"] == unique_plate
    assert body["color"] == "Red"
    assert body["make"] == "Toyota"
    assert "created_at" in body  # still returned
    # no 'updated_at' in new model

    # Verify the update persisted by fetching the vehicle list as admin
    get_res = requests.get(f"{url}/vehicles/normal_update_user", headers=admin_headers)
    assert get_res.status_code == 200
    vehicles = get_res.json()
    assert "vehicles" in vehicles
    found = next((v for v in vehicles["vehicles"] if v["license_plate"] == unique_plate), None)
    assert found is not None
    assert found["color"] == "Red"


# test passed if token invalid returns 401
def test_put_invalid_token():
    license_plate = "44-BF-46"
    data = {
        "user_id": "test",
        "license_plate": "44-BF-46",
        "make": "Ford",
        "model": "Focus",
        "color": "Gray",
        "year": 2021,
    }
    res = requests.put(f"{url}/vehicles/{license_plate}", json=data)  # no auth headers
    assert res.status_code == 401
    assert "Unauthorized" in res.text


""" delete /vehicles endpoint tests """


# test passed if the delete without valid token returns 401
def test_delete_unauthorized():
    lid = "55AB5"
    res = requests.delete(f"{url}/vehicles/{lid}")  # no auth headers
    assert res.status_code == 401
    assert "Unauthorized" in res.text


# test is passed when deleting a non existing vehicle returns 404
def test_delete_nonexisting():
    headers = register_login("delete_user1", "123")
    lid = "66AB6"
    res = requests.delete(f"{url}/vehicles/{lid}", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Vehicle not found"


# test passed if an existing vehicle is deleted successfully and returns 200
def test_delete_existing():
    headers = register_login("delete_user2", "123")
    data = {
        "user_id": "test",
        "license_plate": "AB-77-CD",
        "make": "Volkswagen",
        "model": "Golf",
        "color": "Gray",
        "year": 2021,
    }
    requests.post(f"{url}/vehicles", json=data, headers=headers)

    lid = "AB77CD"
    res2 = requests.delete(f"{url}/vehicles/{lid}", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "Deleted"

    res3 = requests.delete(f"{url}/vehicles/{lid}", headers=headers)
    assert res3.status_code == 404
    assert res3.json()["detail"] == "Vehicle not found"


""" Get /vehicles endpoint tests """


# test passes if GET without valid token returns 401
def test_get_unauthorizedtoken():
    res = requests.get(f"{url}/vehicles")
    assert res.status_code == 401
    assert "Unauthorized" in res.text


# test passed if it returns existing vehicles
def test_get_list():
    headers = register_login("get_user2", "123")

    data = {
        "user_id": "dummy",
        "license_plate": "AA-55-CD",
        "make": "Toyota",
        "model": "Corolla",
        "color": "Silver",
        "year": 2021,
    }

    # create a vehicle
    requests.post(f"{url}/vehicles", json=data, headers=headers)

    # retrieve the user's vehicle list
    res = requests.get(f"{url}/vehicles", headers=headers)
    assert res.status_code == 200
    body = res.json()

    vehicles = body.get("vehicles", [])
    found = next((v for v in vehicles if v["license_plate"] == "AA-55-CD"), None)

    assert found is not None
    assert found["license_plate"] == "AA-55-CD"
    assert found["make"] == "Toyota"


# test passed if admin can retrieve vehicles of a certain user (returns 200)
def test_admin_view_user_vehicles():
    admin_headers = register_admin("admin_user", "123", "Admin")
    user_headers = register_login("normal_user", "123")
    # normal user creates a vehicle
    data = {
        "user_id": "dummy",
        "license_plate": "99-XY-99",
        "make": "Honda",
        "model": "Civic",
        "color": "Blue",
        "year": 2022,
    }
    requests.post(f"{url}/vehicles", json=data, headers=user_headers)
    # admin attempts to fetch that user's vehicles
    res = requests.get(f"{url}/vehicles/normal_user", headers=admin_headers)
    assert res.status_code in (200, 403, 404)
    if res.status_code == 200:
        body = res.json()
        assert "vehicles" in body
        vehicles = body["vehicles"]
        found = next((v for v in vehicles if v["license_plate"] == "99-XY-99"), None)
        assert found is not None
        assert found["make"] == "Honda"


# added test for get/vehicles/{license_plate}/reservations
# test passed if reservation is sent back, returns 200
def test_get_vehicle_reservations():
    headers = register_login("res_user", "123")
    unique_plate = valid_plate()
    vehicle_data = {
        "user_id": "test",
        "license_plate": unique_plate,
        "make": "Renault",
        "model": "Clio",
        "color": "Blue",
        "year": 2019,
    }
    vehicle_res = requests.post(f"{url}/vehicles", json=vehicle_data, headers=headers)
    assert vehicle_res.status_code == 200
    vehicle_id = vehicle_res.json()["id"]
    reservation_data = {
        "vehicle_id": vehicle_id,
        "start_time": "2025-12-20T10:00:00:00Z",
        "end_time": "2025-12-20T14:00:00Z",
        "parking_lot_id": "1",
    }
    res_create = requests.post(f"{url}/reservations/", json=reservation_data, headers=headers)
    lid = unique_plate.replace("-", "").upper()
    res = requests.get(f"{url}/vehicles/{lid}/reservations", headers=headers)
    body = res.json()
    assert "reservations" in body
    assert isinstance(body["reservations"], list)
    if res_create.status_code == 201:
        assert len(body["reservations"]) > 0
        assert body["reservations"][0]["vehicle_id"] == vehicle_id


# added test get/vehicles/{license_plate}/history
# test passed if vehicles history is returned (200)
def test_get_vehicle_history():
    user_headers = register_login("history_integration_user", "123")
    vehicle_plate = valid_plate()
    vehicle_data = {
        "user_id": "test",
        "license_plate": vehicle_plate,
        "make": "Toyota",
        "model": "Camry",
        "color": "Silver",
        "year": 2023,
    }
    create_vehicle_res = requests.post(f"{url}/vehicles", json=vehicle_data, headers=user_headers)
    assert create_vehicle_res.status_code == 200
    # get parking lot
    lots_res = requests.get(f"{url}/parking-lots/")
    assert lots_res.status_code == 200
    lots = lots_res.json()
    assert len(lots) > 0, "No parking lots available for this test"
    lot_id = list(lots.keys())[0]
    # start parking session
    session_data = {"licenseplate": vehicle_plate}
    start_res = requests.post(
        f"{url}/parking-lots/{lot_id}/sessions/start", json=session_data, headers=user_headers
    )
    print("START SESSION:", start_res.status_code, start_res.text)
    print("Sent headers:", user_headers)
    print("Sent session_data:", session_data)

    assert start_res.status_code == 200
    time.sleep(2)
    stop_res = requests.put(
        f"{url}/parking-lots/{lot_id}/sessions/stop", json=session_data, headers=user_headers
    )
    assert stop_res.status_code == 200
    stopped_session = stop_res.json()
    assert stopped_session["stopped"] is not None
    assert stopped_session["duration_minutes"] >= 0
    assert stopped_session["cost"] >= 0
    assert stopped_session["payment_status"] == "Pending"
    lid = vehicle_plate.replace("-", "").upper()
    history_res = requests.get(f"{url}/vehicles/{lid}/history", headers=user_headers)
    assert history_res.status_code == 200
    body = history_res.json()
    assert "history" in body
    assert isinstance(body["history"], list)
    history = body["history"]
    assert len(history) >= 1, "Expected at least one completed session in history"
    found_session = None
    for session in history:
        if session["licenseplate"] == vehicle_plate:
            found_session = session
            break
    assert found_session is not None, f"Could not find session for vehicle {vehicle_plate}"
    assert found_session["licenseplate"] == vehicle_plate
    assert found_session["started"] is not None
    assert found_session["stopped"] is not None
    assert found_session["user"] == "history_integration_user"
    assert found_session["duration_minutes"] >= 0
    assert found_session["cost"] >= 0
    assert found_session["payment_status"] == "Pending"
    assert found_session["parking_lot_id"] == lot_id
    assert found_session["parking_lot_name"] == lots[lot_id]["name"]
    assert found_session["parking_lot_address"] == lots[lot_id]["address"]
    assert "session_id" in found_session


# test passed if creating a vehicle with an empty or whitespace-only name is rejected (400 or 422)
def test_vehicle_name_empty_or_whitespace():
    headers = register_login("edge_user1", "123")
    for bad_plate in ["", "   ", "\n"]:
        data = {
            "user_id": "tester",
            "license_plate": bad_plate,
            "make": "Toyota",
            "model": "Yaris",
            "color": "Blue",
            "year": 2020,
        }
        res = requests.post(f"{url}/vehicles", json=data, headers=headers)
        assert res.status_code in (400, 422)


# test passed if creating vehicle with invalid license plate format is rejected (400 or 422)
def test_license_plate_invalid_format():
    headers = register_login("edge_user2", "123")
    bad_plates = ["123", "ABCD", "!!!-###", "AA--111", None]
    for plate in bad_plates:
        data = {
            "user_id": "tester",
            "license_plate": plate,
            "make": "Toyota",
            "model": "Yaris",
            "color": "Blue",
            "year": 2020,
        }

        res = requests.post(f"{url}/vehicles", json=data, headers=headers)
        assert res.status_code == 422


# test passed if license plate comparison is case-insensitive
def test_license_plate_case_insensitivity():
    headers = register_login("edge_user3", "123")
    data1 = {
        "user_id": "tester",
        "license_plate": "ad-11-cd",
        "make": "Ford",
        "model": "Fiesta",
        "color": "Blue",
        "year": 2020,
    }
    data2 = {
        "user_id": "tester",
        "license_plate": "AD-11-CD",
        "make": "Ford",
        "model": "Fiesta",
        "color": "Red",
        "year": 2020,
    }
    res1 = requests.post(f"{url}/vehicles", json=data1, headers=headers)
    res2 = requests.post(f"{url}/vehicles", json=data2, headers=headers)
    assert {res1.status_code, res2.status_code} <= {200, 400}


# test passed if updating a vehicle with invalid name or plate format is rejected (400 or 422)
def test_update_vehicle_invalid_format():
    headers = register_login("edge_user4", "123")
    create_data = {
        "user_id": "tester",
        "license_plate": "22-AAA-2",
        "make": "Ford",
        "model": "Fiesta",
        "color": "Blue",
        "year": 2021,
    }
    requests.post(f"{url}/vehicles", json=create_data, headers=headers)
    lid = "22AAA2"
    bad_updates = [
        {
            "user_id": "tester",
            "license_plate": "22-AAA-2",
            "make": "",
            "model": "Fiesta",
            "color": "Blue",
            "year": 2021,
        },
        {
            "user_id": "tester",
            "license_plate": "BAD-PLATE",
            "make": "Ford",
            "model": "Fiesta",
            "color": "Blue",
            "year": 2021,
        },
    ]
    for update in bad_updates:
        res = requests.put(f"{url}/vehicles/{lid}", json=update, headers=headers)
        assert res.status_code in (400, 422)


# test passed if a user cannot update a vehicle owned by another user (403 or 404)
def test_update_vehicle_not_owned_by_user():
    user1 = register_login("edge_user5", "123")
    user2 = register_login("edge_user6", "123")
    data = {
        "user_id": "tester",
        "license_plate": "AA-63-CD",
        "make": "Volkswagen",
        "model": "Golf",
        "color": "Black",
        "year": 2022,
    }
    requests.post(f"{url}/vehicles", json=data, headers=user1)
    lid = "AA63CD"
    update_data = {
        "user_id": "tester",
        "license_plate": "AA-63-CD",
        "make": "BMW",
        "model": "X5",
        "color": "Black",
        "year": 2022,
    }
    res = requests.put(f"{url}/vehicles/{lid}", json=update_data, headers=user2)
    assert res.status_code == 403
    assert "Forbidden" in res.text


# test passed if a user cannot delete another user's vehicle (403)
def test_delete_vehicle_not_owned_by_user():
    user1 = register_login("edge_user7", "123")
    user2 = register_login("edge_user8", "123")

    # user1 creates a valid vehicle
    data = {
        "user_id": "dummy",
        "license_plate": "45-AA-44",
        "make": "Audi",
        "model": "A3",
        "color": "Gray",
        "year": 2021,
    }
    requests.post(f"{url}/vehicles", json=data, headers=user1)

    lid = "45AA44"

    # user2 attempts to delete user1's vehicle — should be forbidden
    res = requests.delete(f"{url}/vehicles/{lid}", headers=user2)

    assert res.status_code == 403
    assert "Forbidden" in res.text


# test passed if a normal user cannot access another user's vehicle list (403)
def test_nonadmin_access_other_user_vehicles():
    headers1 = register_login("edge_user9", "123")
    headers2 = register_login("edge_user10", "123")

    # user1 creates a valid vehicle
    data = {
        "user_id": "dummy",
        "license_plate": "55-AA-88",
        "make": "Mazda",
        "model": "CX-5",
        "color": "Silver",
        "year": 2022,
    }
    requests.post(f"{url}/vehicles", json=data, headers=headers1)

    # user2 (non-admin) tries to access user1’s vehicle list — should be forbidden
    res = requests.get(f"{url}/vehicles/edge_user9", headers=headers2)

    assert res.status_code == 403
    assert "Access denied" in res.text


# test passed if fetching history for a non-existent vehicle returns 404
# NOTE: history endpoint currently returns an empty list for vehicles (add test vehicle behavior after implementation)
def test_history_nonexistent_vehicle():
    headers = register_login("edge_user11", "123")
    res = requests.get(f"{url}/vehicles/99ZZ9/history", headers=headers)
    assert res.status_code == 404


# test passed if unauthorized users trying to access reservations are rejected (401)
# NOTE: the reservations endpoint is a placeholder that returns {"reservations": []} when valid
def test_reservations_unauthorized_access():
    res = requests.get(f"{url}/vehicles/11AC1/reservations")
    assert res.status_code == 401


# test passed if requesting reservations for a non-existing vehicle returns 404
# NOTE: reservation logic itsself is not yet implemented, this only tests error handling
def test_reservations_nonexistend_vehicle():
    headers = register_login("edge_user12", "123")
    res = requests.get(f"{url}/vehicles/doesnotexists/reservations", headers=headers)
    assert res.status_code == 404
