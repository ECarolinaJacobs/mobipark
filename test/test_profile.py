import pytest
import requests
from test.test_utils import delete_user

url = "http://localhost:8000"


@pytest.fixture
def test_user():
    return {
        "username": "profiletestuser2",
        "password": "profilepass123",
        "name": "Profile Test Userr"
    }

#a helper method to register and login a user, returning the auth header
@pytest.fixture
def auth_header(test_user):
    delete_user(test_user["username"])
    requests.post(f"{url}/register", json=test_user)

    res = requests.post(f"{url}/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })

    token = res.json()["session_token"]

    return {"Authorization": token}


#get /profile:

# this test checks that a loggedin user can get their profile
def test_get_profile_success(auth_header):
    res = requests.get(f"{url}/profile", headers=auth_header)

    assert res.status_code == 200
    data = res.json()
    assert "username" in data
    assert "name" in data


#this test checks that accessing profile without a token returns 401
def test_get_profile_missing_token():
    res = requests.get(f"{url}/profile")

    assert res.status_code == 401
    assert res.json()["detail"] == "Missing session token"


# this test checks that accessin profile with an invalid token returns 401
def test_get_profile_invalid_token():
    res = requests.get(
        f"{url}/profile",
        headers={"Authorization": "invalid-token"}
    )

    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid session token"


#PUT /profile:

# this checks that a user can update their name successfully
def test_update_profile_name(auth_header):
    update_data = {
        "name": "Updated Name"
    }

    res = requests.put(
        f"{url}/profile",
        json=update_data,
        headers=auth_header
    )

    assert res.status_code == 200
    assert res.json()["message"] == "User updated successfully"

    profile_res = requests.get(
        f"{url}/profile",
        headers=auth_header
    )

    assert profile_res.json()["name"] == "Updated Name"


# this checks that a user can update their password successfully
def test_update_profile_password(test_user):
    delete_user(test_user["username"])
    requests.post(f"{url}/register", json=test_user)

    login_res = requests.post(f"{url}/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })

    token = login_res.json()["session_token"]

    headers = {"Authorization": token}

    new_password = "newsecurepassword123"

    res = requests.put(
        f"{url}/profile",
        json={"password": new_password},
        headers=headers
    )

    assert res.status_code == 200

    bad_login = requests.post(f"{url}/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })
    assert bad_login.status_code == 401

    good_login = requests.post(f"{url}/login", json={
        "username": test_user["username"],
        "password": new_password
    })
    assert good_login.status_code == 200


# this tets checks that updating profile without a token returns 401
def test_update_profile_missing_token():
    res = requests.put(
        f"{url}/profile",
        json={"name": "No Token User"}
    )

    assert res.status_code == 401
    assert res.json()["detail"] == "Missing session token"


# this test checks that updating profile with an invalid token returns 401
def test_update_profile_invalid_token():
    res = requests.put(
        f"{url}/profile",
        json={"name": "Invalid Token"},
        headers={"Authorization": "fake-token"}
    )

    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid session token"
