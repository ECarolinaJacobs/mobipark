import pytest
import requests


url = "http://localhost:8000"

#helper functions to get user&admin tokens
def register_or_login_user(username="testuser", password="testpass", name=None):
    name = name or username
    register_data = {"username": username, "password": password, "name": name}
    res = requests.post(f"{url}/auth/register", json=register_data)

    if res.status_code == 400 and "Username already exists" in res.text:
        login_data = {"username": username, "password": password}
        res = requests.post(f"{url}/auth/login", json=login_data)

    assert res.status_code in (200, 201), f"User auth failed: {res.text}"
    token = res.json().get("session_token")
    assert token, f"No session token returned: {res.text}"

    return {"Authorization": token}

def register_admin(username="admin_user", password="123", name="admin"):
    name = name or username
    register_data = {"username": username, "password": password, "name": name, "role": "ADMIN"}
    res = requests.post(f"{url}/auth/register", json=register_data)
    if res.status_code == 400 and "Username already exists" in res.text:
        res = requests.post(f"{url}/auth/login", json={"username": username, "password": password})
    assert res.status_code in (200, 201), f"Auth failed for {username}: {res.text}"
    token = res.json().get("session_token")
    assert token, f"No token received from auth response: {res.text}"
    return {"Authorization": token}


@pytest.fixture
def user_token():
    return register_or_login_user(username="testuser", password="testpass")["Authorization"]


@pytest.fixture
def admin_token():
    return register_admin(username="admin", password="admin")["Authorization"]


#this test Checks that the /billing endpoint requires authentication.
def test_billing_unauthorized():
    resp = requests.get(f"{url}/billing")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Unauthorized: Invalid or missing session token"


#this test checks that a valid loggedin user can access their billing info.
def test_billing_authorized_empty(user_token):
    headers = {"Authorization": user_token}
    resp = requests.get(f"{url}/billing", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data == []

#this test Checks that the /billing endpoint returns correct billing data if the user has past sessions.
def test_billing_with_sessions(user_token):
    headers = {"Authorization": user_token}
    resp = requests.get(f"{url}/billing", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

    if data:  
        record = data[0]
        assert "session" in record
        assert "parking" in record
        assert "amount" in record
        assert "balance" in record

#this test makes sure that the admin billing endpoint also needs authentication.
def test_billing_admin_unauthorized():
    resp = requests.get(f"{url}/billing/testuser")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Unauthorized: Invalid or missing session token"


#this test makes sure a regular user cannot access another users billing info.
def test_billing_admin_forbidden(user_token):
    headers = {"Authorization": user_token}
    resp = requests.get(f"{url}/billing/otheruser", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "You are not an admin, access denied!"


#this test checks that an admin can access another user's billing info.
def test_billing_admin_valid(admin_token):
    headers = {"Authorization": admin_token}
    resp = requests.get(f"{url}/billing/testuser", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

    if data:  
        record = data[0]
        assert "session" in record
        assert "parking" in record
        assert "amount" in record

#this test checks if admin sends empty list back if user dont exist.
def test_billing_admin_nonexistent_user(admin_token):
    headers = {"Authorization": admin_token}
    resp = requests.get(f"{url}/billing/notarealuser", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data == []