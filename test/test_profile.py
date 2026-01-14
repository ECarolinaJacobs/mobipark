import pytest
import requests
import uuid


url = "http://localhost:8000"


@pytest.fixture
def test_user():
    return {
        "username": f"profiletest_{uuid.uuid4().hex[:8]}",
        "password": "profilepass123",
        "name": "Profile Test User"
    }

#a helper method to register and login a user, returning the auth header
@pytest.fixture
def auth_header(test_user):
    register_res = requests.post(f"{url}/register", json=test_user)
    assert register_res.status_code == 200

    login_res = requests.post(
        f"{url}/login",
        json={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    assert login_res.status_code == 200

    token = login_res.json()["session_token"]
    return {"Authorization": token}


#get /profile:

def test_get_profile_success(auth_header):
    res = requests.get(f"{url}/profile", headers=auth_header)

    assert res.status_code == 200
    data = res.json()

    assert "id" in data
    assert "username" in data
    assert "name" in data
    assert "role" in data
    assert "active" in data

    assert "password" not in data
    assert "hash_type" not in data


def test_get_profile_missing_token():
    res = requests.get(f"{url}/profile")

    assert res.status_code == 401
    assert res.json()["detail"] == "Missing session token"


def test_get_profile_invalid_token():
    res = requests.get(
        f"{url}/profile",
        headers={"Authorization": "invalid-token"}
    )

    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid session token"


#PUT /profile:

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
    assert res.json()["message"] == "Profile updated successfully"

    profile_res = requests.get(
        f"{url}/profile",
        headers=auth_header
    )

    assert profile_res.status_code == 200
    assert profile_res.json()["name"] == "Updated Name"


def test_update_profile_password(test_user):
    register_res = requests.post(f"{url}/register", json=test_user)
    assert register_res.status_code == 200

    login_res = requests.post(
        f"{url}/login",
        json={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    assert login_res.status_code == 200

    token = login_res.json()["session_token"]
    headers = {"Authorization": token}

    new_password = "newsecurepassword123"

    res = requests.put(
        f"{url}/profile",
        json={"password": new_password},
        headers=headers
    )

    assert res.status_code == 200
    assert res.json()["message"] == "Profile updated successfully"

    bad_login = requests.post(
        f"{url}/login",
        json={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    assert bad_login.status_code == 401

    good_login = requests.post(
        f"{url}/login",
        json={
            "username": test_user["username"],
            "password": new_password
        }
    )
    assert good_login.status_code == 200


def test_update_profile_missing_token():
    res = requests.put(
        f"{url}/profile",
        json={"name": "No Token User"}
    )

    assert res.status_code == 401
    assert res.json()["detail"] == "Missing session token"


def test_update_profile_invalid_token():
    res = requests.put(
        f"{url}/profile",
        json={"name": "Invalid Token"},
        headers={"Authorization": "fake-token"}
    )

    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid session token"