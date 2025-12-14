import pytest
import requests
from test.test_utils import create_user, delete_user, get_session
import random

URL = "http://localhost:8000" 


ADMIN_LOGIN = {
    "username": "admin",
    "password": "admin"
}

USER_LOGIN = {
    "username": "test",
    "password": "test"
}


@pytest.fixture(scope="session")
def vehicle_creation_succes():
    try:
        create_user(False)
    except Exception as e:
        print(f"Error creating user: {e}")

    headers = get_session()
    unique_plate = f"AB-{random.randint(10,99)}-{random.randint(10,99)}"
    vehicle_data = {
        "user_id": "TestUser",
        "license_plate": unique_plate,
        "make": "Opel",
        "model": "Crs",
        "color": "Pinkk",
        "year": 2022
    }
    res = requests.post(f"{URL}/vehicles", json=vehicle_data, headers=headers)
    
    vehicle = {}
    if res.status_code == 200:
        vehicle = res.json()
    elif res.status_code == 400 and "already exists" in res.json().get("detail", ""):
        res_get = requests.get(f"{URL}/vehicles", headers=headers) 
        if res_get.status_code == 200 and res_get.json():
             for v in res_get.json():
                 if v.get('license_plate') == unique_plate:
                     vehicle = v
                     break
        if not vehicle:
            pytest.skip("Could not create or retrieve vehicle for test user.")
    else:
        pytest.fail(f"Vehicle creation failed with status {res.status_code}: {res.json()}")

    assert "id" in vehicle, "Vehicle fixture failed to provide a vehicle with an 'id'"

    yield vehicle, headers
    
    if "id" in vehicle:
        requests.delete(f"{URL}/vehicles/{vehicle['id']}", headers=headers)
    
    delete_user()

@pytest.fixture(scope="session")
def vehicle_creation_succes_admin():
    try:
        create_user(True, username=ADMIN_LOGIN["username"], password=ADMIN_LOGIN["password"])
    except Exception as e:
        print(f"User 'admin' might already exist: {e}")

    headers = get_session(username=ADMIN_LOGIN["username"], password=ADMIN_LOGIN["password"])
    
    unique_plate = f"AB-{random.randint(10,99)}-{random.randint(10,99)}"
    vehicle_data = {
        "user_id": "AdminUser",
        "license_plate": unique_plate,
        "make": "BMW",
        "model": "X5",
        "color": "Pinkk",
        "year": 2023
    }
    res = requests.post(f"{URL}/vehicles", json=vehicle_data, headers=headers)
    
    vehicle = {}
    if res.status_code == 200:
        vehicle = res.json()
    elif res.status_code == 400 and "already exists" in res.json().get("detail", ""):
        res_get = requests.get(f"{URL}/vehicles", headers=headers)
        if res_get.status_code == 200 and res_get.json():
            for v in res_get.json():
                if v.get('license_plate') == unique_plate:
                    vehicle = v
                    break
        if not vehicle:
            pytest.skip("Could not create or retrieve vehicle for admin user.")
    else:
        pytest.fail(f"Admin vehicle creation failed with status {res.status_code}: {res.json()}")

    assert "id" in vehicle, "Admin vehicle fixture failed to provide a vehicle with an 'id'"
    
    yield vehicle, headers

    if "id" in vehicle:
        requests.delete(f"{URL}/vehicles/{vehicle['id']}", headers=headers)
    
    delete_user(username=ADMIN_LOGIN["username"])

#======================================================================================
"""POST reservations endpoint tests"""

def test_create_reservation_as_user(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)
    assert res.status_code == 201
    assert res.json()["status"] == "Success"
    reservation = res.json()["reservation"]
    assert reservation["vehicle_id"] == data["vehicle_id"]
    assert reservation["user_id"] == USER_LOGIN["username"]

def test_create_reservation_as_admin(vehicle_creation_succes_admin):
    vehicle, headers = vehicle_creation_succes_admin
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1", "user_id": USER_LOGIN["username"]}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 201
    assert res.json()["status"] == "Success"
    reservation = res.json()["reservation"]
    for key in data:
        assert reservation[key] == data[key]

def test_create_reservation_as_admin_missing_user(vehicle_creation_succes_admin):
    vehicle, headers = vehicle_creation_succes_admin
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 401
    assert res.json()["error"] == "Required field missing"
    assert res.json()["field"] == "user_id"

def test_missing_parking_lot(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z"} 
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert res.json()["detail"][0]["type"] == "missing"
    assert res.json()["detail"][0]["loc"][-1] == "parking_lot_id"
  
def test_missing_vehicle_id():
    create_user(False)
    headers = get_session()
    data = {"start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert res.json()["detail"][0]["type"] == "missing"
    assert res.json()["detail"][0]["loc"][-1] == "vehicle_id"
    delete_user()

def test_missing_start_time(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert res.json()["detail"][0]["type"] == "missing"
    assert res.json()["detail"][0]["loc"][-1] == "start_time"

def test_missing_end_time(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time":  "2025-12-06T10:00Z", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert res.json()["detail"][0]["type"] == "missing"
    assert res.json()["detail"][0]["loc"][-1] == "end_time" 

def test_incorrect_vehicle_id_format():
    create_user(False)
    headers = get_session()
    data = {"vehicle_id": "1233456", "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert "Vehicle id must be a valid uuid" in res.json()["detail"][0]["msg"]
    assert res.json()["detail"][0]["loc"][-1] == "vehicle_id"  
    delete_user()

def test_incorrect_start_time_format(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time": "123456789", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert 'Value error, Date must be in iso format: YYYY-MM-DDTHH:MMZ' in res.json()["detail"][0]["msg"]

def test_incorrect_end_time_format(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "123456", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert 'Value error, Date must be in iso format: YYYY-MM-DDTHH:MMZ' in res.json()["detail"][0]["msg"]

def test_incorrect_parking_lot_id_format(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "Z"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert "Parking lot id must be a digit" in res.json()["detail"][0]["msg"]

def test_parking_lot_id_not_found_user(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "99999"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 404
    assert res.json()["detail"] == "Parking lot not found"

def test_parking_lot_id_not_found_admin(vehicle_creation_succes_admin):
    vehicle, headers = vehicle_creation_succes_admin
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "99999", "user_id": "test"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 404
    assert res.json()["detail"] == "Parking lot not found"

#======================================================================================
"""PUT reservations endpoint tests"""

def test_update_missing_vehicle_id(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"} 
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)
    assert res.status_code == 201
    
    reservation_id = res.json()["reservation"]["id"]
    new_data = {"start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json=new_data, headers=headers)
 
    assert res_put.status_code == 422
    assert res_put.json()["detail"][0]["type"] == "missing"
    assert res_put.json()["detail"][0]["loc"][-1] == "vehicle_id"

def test_update_missing_start_time(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"} 
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)
    assert res.status_code == 201
    
    reservation_id = res.json()["reservation"]["id"]
    new_data = {"vehicle_id": vehicle["id"],"end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json=new_data, headers=headers)
 
    assert res_put.status_code == 422
    assert res_put.json()["detail"][0]["type"] == "missing"
    assert res_put.json()["detail"][0]["loc"][-1] == "start_time"

def test_update_missing_end_time(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"} 
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)
    assert res.status_code == 201
    
    reservation_id = res.json()["reservation"]["id"]
    new_data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06T10:00Z", "parking_lot_id": "1"}
    
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json=new_data, headers=headers)
 
    assert res_put.status_code == 422
    assert res_put.json()["detail"][0]["type"] == "missing"
    assert res_put.json()["detail"][0]["loc"][-1] == "end_time"

def test_update_cost_as_user(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"} 
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)
    assert res.status_code == 201
    
    reservation_id = res.json()["reservation"]["id"]
    new_data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1", "cost": "4567890"}
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json=new_data, headers=headers)

    assert res_put.status_code == 403
    assert "Only admins can modify reservation cost" in res_put.json()["detail"]

def test_update_status_as_user(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"} 
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)
    assert res.status_code == 201
    
    reservation_id = res.json()["reservation"]["id"]
    new_data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1", "status": "confirmed" }
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json=new_data, headers=headers)

    assert res_put.status_code == 403
    assert "Only admins can modify reservation status" in res_put.json()["detail"]

def test_update_invalid_status_as_admin(vehicle_creation_succes_admin):
    vehicle, headers = vehicle_creation_succes_admin
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1", "user_id" : vehicle["user_id"]} 
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)
    assert res.status_code == 201
    
    reservation_id = res.json()["reservation"]["id"]
    new_data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1", "status": "invalid_status", "user_id" : vehicle["user_id"] }
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json=new_data, headers=headers)
    print(res_put.json())
    assert res_put.status_code == 403
    assert "Invalid status" in res_put.json()["detail"]
    
def test_update_reservation_not_found(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    new_data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    res = requests.put(f"{URL}/reservations/9999999999999", json=new_data, headers=headers)

    assert res.status_code == 404
    assert res.json()["detail"] == "Reservation not found"

def test_update_reservation_success(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)
    assert res.status_code == 201

    reservation_id = res.json()["reservation"]["id"]
    new_data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "2"}
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json=new_data, headers=headers)

    assert res_put.status_code == 200   
    assert res_put.json()["status"] == "Updated"
    reservation = res_put.json()["reservation"]
    for key in new_data:
        assert reservation[key] == new_data[key]

#======================================================================================
"""DELETE reservations endpoint tests"""

def test_delete_reservation_deletion_succes(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)
    assert res.status_code == 201

    reservation_id = res.json()["reservation"]["id"]
    res_delete = requests.delete(f"{URL}/reservations/{reservation_id}", headers=headers)
    
    assert res_delete.status_code == 200
    assert res_delete.json()["status"] == "Deleted"
    assert res_delete.json()["id"] == reservation_id

def test_delete_reservation_not_found():
    create_user(False)
    headers = get_session()
    res_delete = requests.delete(f"{URL}/reservations/19999999999999999", headers=headers)

    assert res_delete.status_code == 404
    assert res_delete.json()["detail"] == "Reservation not found"
    delete_user()

#======================================================================================
"""GET reservations endpoint tests"""

def test_get_reservation_succes(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06T10:00Z", "end_time": "2025-12-07T12:00Z", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)
    assert res.status_code == 201
  
    reservation_id = res.json()['reservation']['id']
    
    response = requests.get(f"{URL}/reservations/{reservation_id}", headers=headers)
    
    assert response.status_code == 200
    reservation = response.json()["reservation"]
    assert reservation["id"] == reservation_id

def test_get_reservation_not_found(vehicle_creation_succes):
    vehicle, headers = vehicle_creation_succes
    response = requests.get(f"{URL}/reservations/9999999999999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Reservation not found"