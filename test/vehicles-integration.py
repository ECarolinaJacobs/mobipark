import requests
import pytest


url = "http://localhost:8000/"


# register and login helper method, returns authentication headers for testing purposes
def register_login(username="vehicle_user", password="123"):
    requests.post(
        f"{url}/register",
        json={"username": username, "password": password, "name": "tester vehicle"},
    )
    res = requests.post(
        f"{url}/login", json={"username": username, "password": password}
    )
    assert res.status_code == 200
    ses_token = res.json()["session_token"]
    return {"Authorization": ses_token}


""" POST vehicles endpoint tests"""


# test is passed if unauthorized req returns 401
def test_unauthorized_vehicle():
    data = {"name": "vehicle test", "license_plate": "ABC-999"}
    res = requests.post(f"{url}/vehicles", json=data)
    assert res.status_code == 401
    assert "Unauthorized" in res.text


# test is passed if missing required fields (name and license plate) return 401
def test_missing_fields():
    headers = register_login("vehicle_user", "123")
    data = {"name": "tester vehicle"}  # missing the license plate field
    res = requests.post(f"{url}/vehicles", json=data, headers=headers)

    assert res.status_code == 401
    body = res.json()
    assert body["error"] == "Require field missing"
    assert body["field"] == "license_plate"


# test passed if creating new vehicle returns 201 with status success
def test_vehicle_creation_success():
    headers = register_login("vehicle_user", "123")
    data = {"name": "My car", "license_plate": "88-ABC-8"}
    res = requests.post(f"{url}/vehicles", json=data, headers=headers)
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "Success"
    assert body["vehicle"]["license_plate"] == "88-ABC-8"


# test passed when creating the same vehicle twice, returns 401
def test_vehicle_creating_duplicate():
    headers = register_login("vehicle_user", "123")
    data = {"name": "My car", "license_plate": "88-ABC-8"}
    # first time succeeds
    first = requests.post(f"{url}/vehicles", json=data, headers=headers)
    assert first.status_code == 201
    # second time returns 401
    second = requests.post(f"{url}/vehicles", json=data, headers=headers)
    assert second.status_code == 401
    body = second.json()
    assert body["error"] == "Vehicle already exists"
    assert "data" in body


""" PUT /vehicles endpoint tests """


# test passed if the update without name field returns 401 and an error message
def test_update_vehicle_missing_field():
    headers = register_login("put_user1", "123")
    create_data = {"name": "test car", "license_plate": "11-ABC-1"}
    res1 = requests.post(f"{url}/vehicles", json=create_data, headers=headers)
    assert res1.status_code == 201

    lid = "11ABC1"
    # without name field
    data = {}
    res = requests.put(f"{url}/vehicles/{lid}", json=data, headers=headers)
    assert res.status_code == 401
    body = res.json()
    assert body["error"] == "Require field missing"
    assert body["field"] == "name"


# test passed if trying to update a non-existing vehicle doesnt work but creates a new one instead
def test_update_nonvehicle():
    headers = register_login("put_user2", "123")
    # update license plate
    create_data = {"name": "not real car", "license_plate": "22-ABC-2"}
    lid = "22ABC2"
    res = requests.put(f"{url}/vehicles/{lid}", json=create_data, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "Success"
    assert body["vehicle"]["name"] == "not real car"
    assert body["vehicle"]["license_plate"] == "22-ABC-2"
    assert "created_at" in body["vehicle"]
    assert "updated_at" in body["vehicle"]


# test passed if an existing vehicles name is updated successfully
def test_update_vehicle_existing_name():
    headers = register_login("put_user3", "123")
    create_data = {"name": "real car", "license_plate": "33-ABC-3"}
    res1 = requests.post(f"{url}/vehicles", json=create_data, headers=headers)
    assert res1.status_code == 201
    lid = "33ABC3"
    # update name
    update_data = {"name": "new car", "license_plate": "33-ABC-3"}
    res2 = requests.put(f"{url}/vehicles/{lid}", json=update_data, headers=headers)
    assert res2.status_code == 200
    body = res2.json()
    assert body["status"] == "Success"
    assert body["vehicle"]["name"] == "new car"
    assert body["vehicle"]["license_plate"] == "33-ABC-3"
    assert "updated_at" in body["vehicle"]


# test passed if token invalid returns 401
def test_put_invalid_token():
    lid = "44ABC4"
    data = {"name": "supposed to fail", "license_plate": "44-ABC-4"}
    res = requests.put(f"{url}/vehicles/{lid}", json=data)  # no auth headers
    assert res.status_code == 401
    assert "Unauthorized" in res.text


""" delete /vehicles endpoint tests """


# test passed if the delete without valid token returns 401
def test_delete_unauthorized():
    lid = "55ABC5"
    res = requests.delete(f"{url}/vehicles/{lid}")  # no auth headers
    assert res.status_code == 401
    assert "Unauthorized" in res.text


# test is passed when deleting a non existing vehicle returns 403
def test_delete_nonexisting():
    headers = register_login("delete_user1", "123")
    lid = "66ABC6"
    res = requests.delete(f"{url}/vehicles/{lid}", headers=headers)
    assert res.status_code == 403
    assert "Vehicle not found" in res.text


# test passed if an existing vehicle is deleted successfully and returns 200
def test_delete_existing():
    headers = register_login("delete_user2", "123")
    create_data = {"name": "test car", "license_plate": "77-ABC-7"}
    res1 = requests.post(f"{url}/vehicles", json=create_data, headers=headers)
    assert res1.status_code == 201

    lid = "77ABC7"
    res2 = requests.delete(f"{url}/vehicles/{lid}", headers=headers)
    assert res2.status_code == 200
    body = res2.json()
    assert body["status"] == "Deleted"

    res3 = requests.delete(f"{url}/vehicles/{lid}", headers=headers)
    assert res3.status_code == 403
    assert "Vehicle not found" in res3.text


""" Get /vehicles endpoint tests """


# test passes if GET without valid token returns 401
def test_get_unauthorizedtoken():
    res = requests.get(f"{url}/vehicles")
    assert res.status_code == 401
    assert "Unauthorized" in res.text


# test passed if GET/vehicles returns empty data for new user with no vehicle
def test_get_empty():
    headers = register_login("get_user1", "123")
    res = requests.get(f"{url}/vehicles", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body == {}


# test passed if it returns existing vehicles
def test_get_list():
    headers = register_login("get_user2", "123")
    data = {"name": "car1", "license_plate": "55-AAA-5"}
    requests.post(f"{url}/vehicles", json=data, headers=headers)
    res = requests.get(f"{url}/vehicles", headers=headers)
    assert res.status_code == 200
    body = res.json()
    lid = "55AAA5"
    assert lid in body
    assert body[lid]["license_plate"] == "55-AAA-5"
    assert body[lid]["name"] == "car1"
