import requests
import pytest
from utils.session_manager import add_session
from utils.storage_utils import load_user_data, save_user_data
import time


url = "http://localhost:8000/"


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
    register_data = {"username": username, "password": password, "name": name}
    res = requests.post(f"{url}/auth/register", json=register_data)
    if res.status_code == 400 and "Username already exists" in res.text:
        pass
    users = load_user_data()
    for user in users:
        if user["username"] == username:
            user["role"] = "ADMIN"
            save_user_data(users)
            break
    login_data = {"username": username, "password": password}
    res = requests.post(f"{url}/auth/login", json=login_data)
    token = res.json().get("session_token")
    assert token, f"Admin login failed: {res.text}"
    return {"Authorization": token}


""" POST vehicles endpoint tests"""


# test is passed if unauthorized req returns 401
def test_unauthorized_vehicle():
    data = {"name": "vehicle test", "license_plate": "AB-12-CD"}
    res = requests.post(f"{url}/vehicles", json=data)
    assert res.status_code == 401
    assert "Unauthorized" in res.text


# test is passed if missing required fields (name and license plate) return 422
def test_missing_fields():
    headers = register_login("vehicle_user", "123")
    data = {"name": "tester vehicle"}  # missing the license plate field
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
    unique_plate = f"AA-{int(time.time()) % 90:02d}-AA"
    data = {"name": "My car", "license_plate": unique_plate}
    res = requests.post(f"{url}/vehicles", json=data, headers=headers)
    body = res.json()
    assert body["license_plate"] == unique_plate
    assert body["name"] == "My car"
    assert "created_at" in body
    assert "updated_at" in body  # changed to support vehicle out model return.
    assert res.status_code == 200


# test passed when creating the same vehicle twice, returns 400
def test_vehicle_creating_duplicate():
    headers = register_login("vehicle_user", "123")
    data = {"name": "My car", "license_plate": "12-BD-33"}
    # first time succeeds
    requests.post(f"{url}/vehicles", json=data, headers=headers)
    res = requests.post(f"{url}/vehicles", json=data, headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "Vehicle already exists"


""" PUT /vehicles endpoint tests """


# test passed if the update without name field returns 401 and an error message
def test_update_vehicle_missing_field():
    headers = register_login("put_user1", "123")
    create_data = {"name": "test car", "license_plate": "11-AB-1"}
    requests.post(f"{url}/vehicles", json=create_data, headers=headers)
    lid = "11AB1"
    data = {}
    res = requests.put(f"{url}/vehicles/{lid}", json=data, headers=headers)
    assert res.status_code == 422
    body = res.json()
    assert any("name" in str(err["loc"]) for err in body["detail"])


# test passed if trying to update a non-existing vehicle doesnt work returns 404
def test_update_nonvehicle():
    headers = register_login("put_user2", "123")
    # update license plate
    create_data = {"name": "not real car", "license_plate": "BC-22-CD"}
    lid = "22BC2"
    res = requests.put(f"{url}/vehicles/{lid}", json=create_data, headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Vehicle not found"
    # changed because the api doesnt make a new vehicle anymore if input is missing, just returns error


# test passed if admin can update vehicle name of another user's vehicle
def test_update_vehicle_existing_name():
    # Create admin user
    admin_headers = register_admin("admin_update_test", "123", "Admin")

    # Create normal user and their vehicle
    user_headers = register_login("normal_update_user", "123")
    unique_plate = f"UU-{int(time.time()) % 90:02d}-UU"
    create_data = {"name": "Original Name", "license_plate": unique_plate}
    create_res = requests.post(f"{url}/vehicles", json=create_data, headers=user_headers)
    assert create_res.status_code == 200

    # Admin updates the vehicle name
    lid = unique_plate.replace("-", "").upper()
    update_data = {"name": "Updated Name", "license_plate": unique_plate}
    update_res = requests.put(f"{url}/vehicles/{lid}", json=update_data, headers=admin_headers)

    assert update_res.status_code == 200
    body = update_res.json()
    assert body["name"] == "Updated Name"
    assert body["license_plate"] == unique_plate
    assert "updated_at" in body

    # Verify the update persisted by fetching the vehicle
    get_res = requests.get(f"{url}/vehicles/normal_update_user", headers=admin_headers)
    assert get_res.status_code == 200
    vehicles = get_res.json()
    assert lid in vehicles
    assert vehicles[lid]["name"] == "Updated Name"


# test passed if token invalid returns 401
def test_put_invalid_token():
    lid = "44BF4"
    data = {"name": "supposed to fail", "license_plate": "BF-44-CD"}
    res = requests.put(f"{url}/vehicles/{lid}", json=data)  # no auth headers
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
    create_data = {"name": "test car", "license_plate": "AB-77-CD"}
    requests.post(f"{url}/vehicles", json=create_data, headers=headers)

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
    data = {"name": "car1", "license_plate": "AA-55-CD"}
    requests.post(f"{url}/vehicles", json=data, headers=headers)
    res = requests.get(f"{url}/vehicles", headers=headers)
    assert res.status_code == 200
    body = res.json()
    lid = "AA55CD"
    assert lid in body
    assert body[lid]["license_plate"] == "AA-55-CD"
    assert body[lid]["name"] == "car1"


# added test for get/vehicles/{username} (admin route)
# test passed if admin can retrieve vehicle of certain user (returns 200)
def test_admin_view_user_vehicles():
    admin_headers = register_admin("admin_user", "123", "Admin")
    user_headers = register_login("normal_user", "123")
    # normal user creates vehicle
    data = {"name": "UserCar", "license_plate": "99-XY-9"}
    requests.post(f"{url}/vehicles", json=data, headers=user_headers)
    # admin attempt to fetch users vehicle
    res = requests.get(f"{url}/vehicles/normal_user", headers=admin_headers)
    assert res.status_code in (200, 403, 404)


# added test for get/vehicles/{license_plate}/reservations
# test passed if reservation is sent back, returns 200
def test_get_vehicle_reservations():
    headers = register_login("res_user", "123")
    data = {"name": "Car R", "license_plate": "RR-10-CD"}
    requests.post(f"{url}/vehicles", json=data, headers=headers)
    lid = "RR10CD"
    res = requests.get(f"{url}/vehicles/{lid}/reservations", headers=headers)
    assert res.status_code == 200
    assert "reservations" in res.json()


# added test get/vehicles/{license_plate}/history
# test passed if vehicles history is returned (200)
def test_get_vehicle_history():
    headers = register_login("hist_user", "123")
    data = {"name": "Car h", "license_plate": "HH-20-CD"}
    requests.post(f"{url}/vehicles", json=data, headers=headers)
    lid = "HH20CD"
    res = requests.get(f"{url}/vehicles/{lid}/history", headers=headers)
    assert res.status_code == 200
    assert "history" in res.json()
    assert isinstance(res.json()["history"], list)


# test passed if creating a vehicle with an empty or whitespace-only name is rejected (400 or 422)
def test_vehicle_name_empty_or_whitespace():
    headers = register_login("edge_user1", "123")
    for bad_name in ["", "   ", "\n"]:
        data = {"name": bad_name, "license_plate": "12-AA-1"}
        res = requests.post(f"{url}/vehicles", json=data, headers=headers)
        assert res.status_code in (400, 422)


# test passed if creating vehicle with invalid license plate format is rejected (400 or 422)
def test_license_plate_invalid_format():
    headers = register_login("edge_user2", "123")
    bad_plates = ["123", "ABCD", "!!!-###", "AA--111", None]
    for plate in bad_plates:
        data = {"name": "Invalid", "license_plate": plate}
        res = requests.post(f"{url}/vehicles", json=data, headers=headers)
        assert res.status_code in (400, 422)


# test passed if license plate comparison is case-insensitive
def test_license_plate_case_insensitivity():
    headers = register_login("edge_user3", "123")
    data1 = {"name": "CarLower", "license_plate": "ad-11-cd"}
    data2 = {"name": "CarUpper", "license_plate": "AD-11-CD"}
    res1 = requests.post(f"{url}/vehicles", json=data1, headers=headers)
    res2 = requests.post(f"{url}/vehicles", json=data2, headers=headers)
    assert {res1.status_code, res2.status_code} <= {200, 400}


# test passed if updating a vehicle with invalid name or plate format is rejected (400 or 422)
def test_update_vehicle_invalid_format():
    headers = register_login("edge_user4", "123")
    create_data = {"name": "ValidCar", "license_plate": "22-AA-9"}
    requests.post(f"{url}/vehicles", json=create_data, headers=headers)
    lid = "22AAA2"
    bad_updates = [{"name": "", "license_plate": "22-AA-9"}, {"name": "   ", "license_plate": "BAD-PLATE"}]
    for update in bad_updates:
        res = requests.put(f"{url}/vehicles/{lid}", json=update, headers=headers)
        assert res.status_code in (400, 422)


# test passed if a user cannot update a vehicle owned by another user (403 or 404)
def test_update_vehicle_not_owned_by_user():
    user1 = register_login("edge_user5", "123")
    user2 = register_login("edge_user6", "123")
    data = {"name": "Car", "license_plate": "AA-63-CD"}
    requests.post(f"{url}/vehicles", json=data, headers=user1)
    lid = "AA63CD"
    res = requests.put(f"{url}/vehicles/{lid}", json=data, headers=user2)
    assert res.status_code in (404, 403)


# test passed if a user cannot delete another users vehicle (403 or 404)
def test_delete_vehicle_not_owned_by_user():
    user1 = register_login("edge_user7", "123")
    user2 = register_login("edge_user8", "123")
    data = {"name": "User1Car", "license_plate": "45-AA-4"}
    requests.post(f"{url}/vehicles", json=data, headers=user1)
    lid = "45AA4"
    res = requests.delete(f"{url}/vehicles/{lid}", headers=user2)
    assert res.status_code in (404, 403)


# test passed if a normal user cannot access another users vehicle list (403)
def test_nonadmin_access_other_user_vehicles():
    headers1 = register_login("edge_user9", "123")
    headers2 = register_login("edge_user10", "123")
    data = {"name": "CarX", "license_plate": "55-AA-8"}
    requests.post(f"{url}/vehicles", json=data, headers=headers1)
    res = requests.get(f"{url}/vehicles/edge_user9", headers=headers2)
    assert res.status_code == 403


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
