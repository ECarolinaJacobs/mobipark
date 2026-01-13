import requests
import pytest
from dotenv import load_dotenv

load_dotenv()

url = "http://localhost:8000/"

# Helper function to register and login a user
def register_login(username="billing_user", password="123", name=None, role="USER"):
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

# Helper function to register and login an admin user
def register_admin(username="admin_billing", password="123", name="Admin"):
    from test.test_utils import update_user_role
    
    name = name or username
    register_data = {"username": username, "password": password, "name": name}
    res = requests.post(f"{url}/auth/register", json=register_data)

    if res.status_code == 400 and "Username already exists" in res.text:
        update_user_role(username, "ADMIN")
        res = requests.post(f"{url}/auth/login", json={"username": username, "password": password})
    else:
        update_user_role(username, "ADMIN")
        res = requests.post(f"{url}/auth/login", json={"username": username, "password": password})

    assert res.status_code in (200, 201), f"Auth failed for {username}: {res.text}"
    token = res.json().get("session_token")
    assert token, f"No token received from auth response: {res.text}"
    return {"Authorization": token}


# GET /billing endpoint tests

# accessing billing without auth returns 401
def test_billing_unauthorized():
    res = requests.get(f"{url}/billing")
    assert res.status_code == 401
    assert "Unauthorized" in res.text

# accessing billing with invalid token returns 401
def test_billing_invalid_token():
    headers = {"Authorization": "invalid_token_12345"}
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 401
    assert "Unauthorized" in res.text

# GET /billing endpoint tests (User)
def test_billing_get_user_own_billing():
    headers = register_login("billing_test_user1", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    assert isinstance(billing_data, list)
    
    if len(billing_data) > 0:
        record = billing_data[0]
        assert "session" in record
        assert "parking" in record
        assert "amount" in record
        assert "thash" in record
        assert "payed" in record
        assert "balance" in record
        
        # session structure
        assert "license_plate" in record["session"]
        assert "started" in record["session"]
        assert "hours" in record["session"]
        assert "days" in record["session"]
        
        # parking structure
        assert "name" in record["parking"]
        assert "location" in record["parking"]
        assert "tariff" in record["parking"]
        assert "daytariff" in record["parking"]

# a new user with no sessions gets empty billing
def test_billing_empty_for_new_user():
    headers = register_login("new_billing_user", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    assert isinstance(billing_data, list)
    assert len(billing_data) == 0

# Test that balance is correctly calculated as amount - payed
def test_billing_balance_calculation():
    headers = register_login("billing_balance_user", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    
    for record in billing_data:
        expected_balance = record["amount"] - record["payed"]
        assert abs(record["balance"] - expected_balance) < 0.01, \
            f"Balance mismatch: expected {expected_balance}, got {record['balance']}"

# Test that hours and days are correctly calculated
def test_billing_hours_and_days_calculation():
    headers = register_login("billing_calc_user", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    
    for record in billing_data:
        hours = record["session"]["hours"]
        days = record["session"]["days"]
        
        # Days should be integer division of hours by 24
        expected_days = int(hours // 24)
        assert days == expected_days, \
            f"Days mismatch: expected {expected_days}, got {days} for {hours} hours"


# GET /billing/{username} endpoint tests (Admin)

#Test that non-admin users cannot access other users' billing
def test_billing_admin_unauthorized_non_admin():
    user_headers = register_login("regular_user_billing", "123")
    
    res = requests.get(f"{url}/billing/some_other_user", headers=user_headers)
    assert res.status_code == 403
    assert "not an admin" in res.text.lower() or "access denied" in res.text.lower()

#Test that accessing admin billing endpoint without token returns 401
def test_billing_admin_unauthorized_missing_token():
    res = requests.get(f"{url}/billing/some_user")
    assert res.status_code == 401
    assert "Unauthorized" in res.text

# Test that admin can access other users' billing information
def test_billing_admin_can_access_user_billing():
    admin_headers = register_admin("admin_billing_test", "123")
    user_headers = register_login("target_billing_user", "123")
    
    # Admin accesses target user's billing
    res = requests.get(f"{url}/billing/target_billing_user", headers=admin_headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    assert isinstance(billing_data, list)

# Test that accessing billing for non-existent user returns empty list
def test_billing_admin_nonexistent_user():
    admin_headers = register_admin("admin_billing_test2", "123")
    
    res = requests.get(f"{url}/billing/nonexistent_user_xyz", headers=admin_headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    assert isinstance(billing_data, list)
    assert len(billing_data) == 0

# Test that admin can view their own billing via admin endpoint
def test_billing_admin_can_view_own_billing():
    admin_headers = register_admin("admin_self_billing", "123")
    
    res = requests.get(f"{url}/billing/admin_self_billing", headers=admin_headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    assert isinstance(billing_data, list)


#edge cases

# Test billing includes active sessions 
def test_billing_with_active_session():
    headers = register_login("active_session_user", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    
    active_sessions = [r for r in billing_data if r["session"]["stopped"] is None]

    # Active sessions should be 0 hours, days, and amount
    for record in active_sessions:
        assert record["session"]["hours"] == 0.0
        assert record["session"]["days"] == 0
        assert record["amount"] == 0.0

# Test billing shows zero balance for fully paid sessions
def test_billing_with_fully_paid_session():
    headers = register_login("paid_session_user", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    
    fully_paid = [r for r in billing_data if r["payed"] >= r["amount"] and r["amount"] > 0]
    for record in fully_paid:
        assert record["balance"] <= 0.01, f"Fully paid session should have ~0 balance, got {record['balance']}"

# Test billing shows positive balance for unpaid sessions
def test_billing_with_unpaid_session():
    headers = register_login("unpaid_session_user", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    
    unpaid = [r for r in billing_data if r["payed"] == 0 and r["amount"] > 0]
    for record in unpaid:
        assert record["balance"] == record["amount"], \
            f"Unpaid session balance should equal amount: {record['amount']}, got {record['balance']}"

# Test billing shows correct balance for partially paid sessions
def test_billing_with_partial_payment():
    headers = register_login("partial_payment_user", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    
    partial = [r for r in billing_data if 0 < r["payed"] < r["amount"]]
    for record in partial:
        expected_balance = record["amount"] - record["payed"]
        assert abs(record["balance"] - expected_balance) < 0.01, \
            f"Partial payment balance mismatch: expected {expected_balance}, got {record['balance']}"

#all billing records have a transaction hash
def test_billing_transaction_hash_exists():
    headers = register_login("hash_check_user", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    
    for record in billing_data:
        assert "thash" in record
        assert isinstance(record["thash"], str)
        assert len(record["thash"]) > 0, "Transaction hash should not be empty"

# Test that user can have multiple sessions with the same license plate
def test_billing_multiple_sessions_same_license():
    headers = register_login("multi_session_user", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    
    # Group by license plate
    license_plates = {}
    for record in billing_data:
        plate = record["session"]["license_plate"]
        if plate not in license_plates:
            license_plates[plate] = []
        license_plates[plate].append(record)
    
    assert isinstance(billing_data, list)

# Test that tariff values are positive numbers
def test_billing_tariff_values_positive():
    headers = register_login("tariff_check_user", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    
    for record in billing_data:
        assert record["parking"]["tariff"] >= 0, "Hourly tariff should be non-negative"
        assert record["parking"]["daytariff"] >= 0, "Day tariff should be non-negative"

# Test that billing response follows the expected schema
def test_billing_response_format():
    headers = register_login("format_check_user", "123")
    
    res = requests.get(f"{url}/billing", headers=headers)
    assert res.status_code == 200
    
    billing_data = res.json()
    assert isinstance(billing_data, list)
    
    required_fields = ["session", "parking", "amount", "thash", "payed", "balance"]
    session_fields = ["license_plate", "started", "hours", "days"]
    parking_fields = ["name", "location", "tariff", "daytariff"]
    
    for record in billing_data:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"
        
        for field in session_fields:
            assert field in record["session"], f"Missing session field: {field}"
        
        for field in parking_fields:
            assert field in record["parking"], f"Missing parking field: {field}"
        
        assert isinstance(record["amount"], (int, float))
        assert isinstance(record["payed"], (int, float))
        assert isinstance(record["balance"], (int, float))
        assert isinstance(record["session"]["hours"], (int, float))
        assert isinstance(record["session"]["days"], int)