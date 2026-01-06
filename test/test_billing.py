import pytest
import requests
from test.test_utils import create_user

url = "http://localhost:8000"

def login(username, password):
    res = requests.post(f"{url}/login", json={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["session_token"]

@pytest.fixture
def user_token():
    create_user(False, "testuser", "testpass")
    return login("testuser", "testpass")

@pytest.fixture
def admin_token():
    create_user(True, "admin", "admin")
    return login("admin", "admin")

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