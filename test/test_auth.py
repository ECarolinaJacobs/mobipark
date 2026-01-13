import pytest
import requests
import random
import string
import uuid

url = "http://localhost:8000"


@pytest.fixture
def test_user():
    unique_id = uuid.uuid4().hex[:8]
    return {"username": f"edgeuser_{unique_id}", "password": "edgepass123", "name": "Edge testperson9"}


# tests if a new user can register successfully and receives a session token, and an Authorization header.
def test_register_user(test_user):
    res = requests.post(f"{url}/auth/register", json=test_user)
    assert res.status_code == 200
    data = res.json()
    assert "session_token" in data
    assert "Authorization" in res.headers


# this test Checks that registering the same username twice returns a 400 error with “Username already exists.”
def test_register_existing_user(test_user):
    requests.post(f"{url}/register", json=test_user)
    res = requests.post(f"{url}/register", json=test_user)
    assert res.status_code == 400
    assert res.json()["detail"] == "Username already exists"


# Confirms that a registered user can log in and gets a valid session token and Authorization header.
def test_login_user(test_user):
    requests.post(f"{url}/auth/register", json=test_user)
    login_data = {"username": test_user["username"], "password": test_user["password"]}
    res = requests.post(f"{url}/auth/login", json=login_data)
    assert res.status_code == 200
    data = res.json()
    assert "session_token" in data
    assert "Authorization" in res.headers


# this test checks if the registration fails with a 400 error,
# when username, password or name are missing or empty.
def test_register_missing_fields():
    bad_user = {"username": "", "password": "abc", "name": ""}
    res = requests.post(f"{url}/register", json=bad_user)
    assert res.status_code == 400
    assert "Missing credentials" in res.text


# this test checks if login fails with a 400 error when username or password is missing.
def test_login_missing_fields():
    res = requests.post(f"{url}/login", json={"username": "", "password": ""})
    assert res.status_code == 400
    assert res.json()["detail"] == "Missing credentials"


# Tests that logging in with an incorrect password returns a 401 “Invalid credentials” error.
def test_login_wrong_password(test_user):
    requests.post(f"{url}/register", json=test_user)

    bad_login = {"username": test_user["username"], "password": "wrongpass"}
    res = requests.post(f"{url}/login", json=bad_login)
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid credentials"


# this test makes sure login fails with 401 when the username does not exist in the system.
def test_login_nonexistent_user():
    res = requests.post(f"{url}/login", json={"username": "idontexist", "password": "fake"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid credentials"


# this test checks that a logged in user can log out successfully when using a valid session token.
def test_logout_valid_token(test_user):
    requests.post(f"{url}/register", json=test_user)

    login_res = requests.post(
        f"{url}/login", json={"username": test_user["username"], "password": test_user["password"]}
    )
    token = login_res.json()["session_token"]

    res = requests.post(f"{url}/logout", params={"token": token})
    assert res.status_code == 200
    assert res.json()["message"] == "User logged out"


# this test Checks that attempting to log out with an invalid or
#  fake token returns a 404 “No active session found.”
def test_logout_invalid_token():
    res = requests.post(f"{url}/logout", params={"token": "fake-token"})
    assert res.status_code == 404
    assert res.json()["detail"] == "No active session found"


# this test checks that the same user can log in multiple times and receives different
# unique session tokens each time.
def test_multiple_logins_same_user(test_user):
    requests.post(f"{url}/register", json=test_user)
    res1 = requests.post(f"{url}/login", json=test_user)

    res2 = requests.post(f"{url}/login", json=test_user)
    assert res1.status_code == 200
    assert res2.status_code == 200
    token1 = res1.json()["session_token"]
    token2 = res2.json()["session_token"]
    assert token1 != token2


# this test makes sure the system handles registration attempts with an extremely long username
def test_register_long_username():
    long_user = {"username": "a" * 255, "password": "securepass", "name": "Long User"}
    res = requests.post(f"{url}/register", json=long_user)
    assert res.status_code in (200, 400)

    if res.status_code == 200:
        token = res.json()["session_token"]
        requests.post(f"{url}/logout", params={"token": token})


# this test checks that usernames that have special characters
# are rejected with a 400 status code.
def test_register_with_special_chars():
    special_user = {"username": "user.name-test_01", "password": "password123", "name": "Special User"}
    res = requests.post(f"{url}/register", json=special_user)
    assert res.status_code == 400


# this test makes sure that login is case sensitive for usernames
def test_login_case_sensitivity(test_user):
    requests.post(f"{url}/register", json=test_user)

    bad_case = {"username": test_user["username"].upper(), "password": test_user["password"]}
    res = requests.post(f"{url}/login", json=bad_case)
    assert res.status_code == 401
