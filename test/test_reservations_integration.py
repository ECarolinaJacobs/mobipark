import pytest
import requests
from test.test_utils import create_user, delete_user, get_session

URL = "http://localhost:8000/"


ADMIN_LOGIN = {
    "username": "admin",
    "password": "admin"
}

USER_LOGIN = {
    "username": "test",
    "password": "test"
}

# def test_create_new_account():
#     data = {
#     "username": "test",
#     "password": "test"
# }
#     url = "http://localhost:8000/register"
#     res = requests.post(url, json=data)

#     assert res.status_code == 200

def login(role: str = "user"):
    """Login and return authorization headers"""
    credentials = USER_LOGIN if role == "USER" else ADMIN_LOGIN
    res = requests.post(url=f"{URL}login", json=credentials)
    assert res.status_code == 200, f"Login failed: {res.json()}"
    token = res.json()["session_token"]
    return {"Authorization": token}


# def test_poep():
#     create_user(True)
#     headers = get_session()
#     data = {"name": "My car", "license_plate": "AF-12-CD"}
#     res = requests.post(f"{URL}/vehicles", json=data, headers=headers)

#     assert res.status_code == 200
#     res = res.json()
#     assert res["license_plate"] == "AF-12-CD"
#     assert res["name"] == "My car"
#     assert "created_at" in res
#     assert "updated_at" in res  # changed to support vehicle out model return.
#     delete_user()
#     return res
    
# Register vehicle helper method for testing purposes.
def test_vehicle_creation_success():
    #false is user and true is admin
    create_user(False)
    headers = get_session()
    data = {"name": "My car", "license_plate": "AF-12-CD"}
    res = requests.post(f"{URL}/vehicles", json=data, headers=headers)

    assert res.status_code == 200
    res = res.json()
    assert res["license_plate"] == "AF-12-CD"
    assert res["name"] == "My car"
    assert "created_at" in res
    assert "updated_at" in res  # changed to support vehicle out model return.
    delete_user()
    print(f"vehicle created: {res}")
    return res


#======================================================================================
"""POST reservations endpoint tests"""

# Test if creating a reservation as a user with a registered vehicle is succesfull with status code 201.
def test_create_reservation_as_user():
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-04","end_time":"2025-12-05", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    
    assert res.status_code == 201
    assert res.json()["status"] == "Success"
    reservation = res.json()["reservation"]
    for key in data:
        assert reservation[key] == data[key]
    delete_user()

# Test if creating a reservation as a admin for a user with a registered vehicle is succesfull with status code 201.
def test_create_reservation_as_admin():
    create_user(True)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-04","end_time":"2025-12-05", "parking_lot_id": "1", "user": USER_LOGIN["username"]}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 201
    #assert res.json()["status"] == "Success"
    reservation = res.json()["reservation"]
    for key in data:
        assert reservation[key] == data[key]
    delete_user()
    

# Test if an error occurs when trying to create a reservation for a user as an admin and the required user field is missing with status code 401.
def test_create_reservation_as_admin_missing_user():
    create_user(True)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-04","end_time":"2025-12-05", "parking_lot_id": "1"} #missing user field
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 401
    assert res.json()["error"] == "Required field missing"
    assert res.json()["field"] == "user" #indicates that the user field is missing
    delete_user()


# Test missing required fields
def test_missing_parking_lot():
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-10-11", "end_time": "2025-10-12"} 
    res = requests.post(f"{URL}/reservations/", json= data, headers=headers)

    assert res.status_code == 422
    assert res.json()["error"] == "Required field missing"
    assert res.json()["field"] == "parking_lot_id" 
    delete_user()

def test_missing_vehicle_id():
    create_user(False)
    headers = get_session()
    data = { "start_time": "2025-10-11", "end_time": "2025-10-12", "parking_lot_id": "1"} # missing vehicle_id field
    res = requests.post(f"{URL}/reservations/", json= data, headers=headers)

    assert res.status_code == 422
    assert res.json()[""]["error"] == "Required field missing"
    assert res.json()["field"] == "vehicle_id"
    delete_user()

def test_missing_start_time():
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"], "end_time": "2025-10-12", "parking_lot_id": "1"} # missing start_time field
    res = requests.post(f"{URL}/reservations/", json= data, headers=headers)

    assert res.status_code == 422
    assert res.json()["error"] == "Required field missing"
    assert res.json()["field"] == "start_time"
    delete_user()

def test_missing_end_time():
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-10-11", "parking_lot_id": "1"} # missing end_time field
    res = requests.post(f"{URL}/reservations/", json= data, headers=headers)

    assert res.status_code == 422
    assert res.json()["error"] == "Required field missing"
    assert res.json()["field"] == "end_time" 
    delete_user()


#Incorrect missing field type tests

def test_incorrect_vehicle_id_format():
    create_user(False)
    headers = get_session()
    data = {"vehicle_id": "1233456", "start_time": "2025-10-11", "end_time": "2025-10-12", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert res.json()["error"] == "Incorrect field format"
    assert res.json()["field"] == "vehicle_id"  
    delete_user()


def test_incorrect_start_time_format():
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"], "start_time": "123456", "end_time": "2025-10-12", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert res.json()["error"] == "Incorrect field format"
    assert res.json()["field"] == "start_time" 
    delete_user()


def test_incorrect_end_time_format():
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-10-11", "end_time": "123456", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert res.json()["error"] == "Incorrect field format"
    assert res.json()["field"] == "end_time" 
    delete_user()


def test_incorrect_parking_lot_id_format():
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-10-11", "end_time": "2025-10-12", "parking_lot_id": "Z"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 422
    assert res.json()["error"] == "Incorrect field format"
    assert res.json()["field"] == "parking_lot_id" 
    delete_user()

# Test if an error occurs when trying to create a reservation for the vehicle of a parking lot that doesn't exist with status code 404.
def test_parking_lot_id_not_found_user():
    #false is user and true is admin
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-10-11", "end_time": "2025-10-12", "parking_lot_id": "Z"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 404
    assert res.json()["detail"] == "Parking lot not found"
    delete_user()

def test_parking_lot_id_not_found_admin():
    #false is user and true is admin
    create_user(True)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-10-11", "end_time": "2025-10-12", "parking_lot_id": "Z"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 404
    assert res.json()["detail"] == "Parking lot not found"
    delete_user()
    


#======================================================================================
"""PUT reservations endpoint tests"""

# Test missing required fields

def test_update_missing_vehicle_id():
    #false is user and true is admin
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-10-11", "end_time": "2025-10-12","parking_lot_id": "3"} 
    res = requests.post(f"{URL}/reservations/", json= data, headers=headers)
    assert res.status_code == 201
    
    reservation_id = res.json()["reservation"]["id"]
    print(f"reservation id:: {reservation_id}")
    new_data = {"start_time": "2025-10-11","end_time": "2025-10-12","parking_lot_id": "1"}
    
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json= new_data, headers=headers)
 
    assert res_put.status_code == 422
    assert res_put.json()["error"] == "Required field missing"
    assert res_put.json()["field"] == "vehicle_id" #indicates which field is missing
    delete_user()

def test_update_missing_start_time():
    #false is user and true is admin
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-10-11", "end_time": "2025-10-12","parking_lot_id": "3"} 
    res = requests.post(f"{URL}/reservations/", json= data, headers=headers)
    assert res.status_code == 201
    
    reservation_id = res.json()["reservation"]["id"]
    print(f"reservation id:: {reservation_id}")
    new_data = {"vehicle_id": vehicle["id"], "end_time": "2025-10-12","parking_lot_id": "1"}
    
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json= new_data, headers=headers)
 
    assert res_put.status_code == 422
    assert res_put.json()["error"] == "Required field missing"
    assert res_put.json()["field"] == "start_time"
    delete_user()

def test_update_missing_end_date():
    #false is user and true is admin
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"], "start_time": "2025-10-11", "end_time": "2025-10-12","parking_lot_id": "3"} 
    res = requests.post(f"{URL}/reservations/", json= data, headers=headers)
    assert res.status_code == 201
    
    reservation_id = res.json()["reservation"]["id"]
    print(f"reservation id:: {reservation_id}")
    new_data = {"vehicle_id": vehicle["id"], "start_time": "2025-10-11","parking_lot_id": "1"}
    
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json= new_data, headers=headers)
 
    assert res_put.status_code == 422
    assert res_put.json()["error"] == "Required field missing"
    assert res_put.json()["field"] == "end_time" 
    delete_user()


def test_update_missing_parking_lot_id():
    #false is user and true is admin
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-10-11", "end_time": "2025-10-12", "parking_lot_id": "1"} 
    res = requests.post(f"{URL}/reservations/", json= data, headers=headers)
    assert res.status_code == 201
    
    reservation_id = res.json()["reservation"]["id"]
    print(f"reservation id:: {reservation_id}")
    new_data = {"vehicle_id": vehicle["id"],"start_time": "2025-10-11", "end_time": "2025-10-12",}
    
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json= new_data, headers=headers)
 
    assert res_put.status_code == 422
    assert res_put.json()["error"] == "Required field missing"
    assert res_put.json()["field"] == "parking_lot_id"
    delete_user()
    
    
    
# Test if an error occurs when the reservation id is not found in the json file with status code 404.
def test_update_reservation_not_found():
    #false is user and true is admin
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    new_data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06","end_time":"2025-12-07", "parking_lot_id": "1"}
    res = requests.put(f"{URL}/reservations/9999999999999", json=new_data, headers=headers)

    assert res.status_code == 404
    assert res.json()["detail"] == "Reservation not found"
    delete_user()
    

# Test if updating a reservation as a user is updated with status code 200.
def test_update_reservation_success():
    #false is user and true is admin
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"] ,"start_time": "2025-12-06","end_time":"2025-12-07", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    assert res.status_code == 201

    reservation_id = res.json()['id']
    new_data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06","end_time":"2025-12-08", "parking_lot_id": "1"}
    res_put = requests.put(f"{URL}/reservations/{reservation_id}", json=new_data, headers=headers)

    assert res_put.status_code == 200   
    assert res_put.json()["status"] == "Updated"
    reservation = res_put.json()
    for key in new_data:
        assert reservation[key] == new_data[key]
    delete_user()

#======================================================================================
"""DELETE reservations endpoint tests"""

# Test if a deletion is possible and give status code 200.
def test_delete_reservation_deletion_succes():
    #false is user and true is admin
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06","end_time":"2025-12-07", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)
    assert res.status_code == 201

    reservation_id = res.json()["id"]
    res_delete = requests.delete(f"{URL}/reservations/{reservation_id}", headers=headers)
    
    assert res_delete.status_code == 200
    assert res_delete.json()["status"] == "Deleted"
    assert res_delete.json()["id"] == reservation_id
    delete_user()
    

# Test to see if an error occurs when a user that is not an admin or not the owner of the reservation can delete the reservation with status code 403.
def test_delete_reservation_nonowner_nonadmin():
    #false is user and true is admin
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06","end_time":"2025-12-07", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json=data, headers=headers)

    reservation_id = res.json()['id']

    assert not headers['role'] == "ADMIN" or not "random_username" == reservation_id["user"]
    assert res.status_code == 403
    assert res.json()["detail"] == "Access denied"
    delete_user()

# Test to see if an error occurs when a reservation id is not found with status code 404.
def test_reservation_not_found():
    create_user(False)
    headers = get_session()
    res_delete = requests.delete(f"{URL}/reservations/19999999999999999", headers=headers)

    assert res_delete.status_code == 404
    assert res_delete.json()["detail"] == "Reservation not found"
    delete_user()

#======================================================================================
"""GET reservations endpoint tests"""

# Test to see if an error occurs when a user that is not an admin and not the owner of the reservation can delete the reservation with status code 403.
def test_get_reservation_nonower_nonadmin():
    #false is user and true is admin
    create_user(False)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06","end_time":"2025-12-07", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json= data, headers=headers)

    reservation_id = res.json()['id']

    assert not headers['role'] == "ADMIN" and not "random_username" == reservation_id["user"]
    assert res.status_code == 403
    assert res.json()["detail"] == "Access denied"
    delete_user()

# Test to see if getting a reservation by id is succesfull with status code 200
def test_get_reservation_succes():
    #false is user and true is admin
    create_user(True)
    headers = get_session()
    vehicle = test_vehicle_creation_success()
    data = {"vehicle_id": vehicle["id"],"start_time": "2025-12-06","end_time":"2025-12-07", "parking_lot_id": "1"}
    res = requests.post(f"{URL}/reservations/", json= data, headers=headers)

    reservation_id = res.json()['id']
    res = requests.get(f"{URL}/reservations/{reservation_id}", headers=headers)

    assert res.status_code == 200
    delete_user()
    

