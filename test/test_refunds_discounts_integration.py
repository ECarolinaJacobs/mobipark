import pytest
import requests
from datetime import datetime, timedelta
import uuid
import test.test_utils

BASE_URL = "http://localhost:8000/"

# User credentials
USER_LOGIN = {
    "username": "test",
    "password": "test",
}

ADMIN_LOGIN = {
    "username": "admin",
    "password": "admin",
}

USER_REGISTER = {
    "username": "test",
    "password": "test",
    "name": "test"
}

ADMIN_REGISTER = {
    "username": "admin",
    "password": "admin",
    "name": "admin"
}

def login(role: str = "user"):
    if role == "user":
        res = requests.post(f"{BASE_URL}register", json=USER_REGISTER)
    else:
        res = requests.post(f"{BASE_URL}register", json=ADMIN_REGISTER)
        # Promote to admin after registration
        test.test_utils.update_user_role("admin", "ADMIN")
    """Login and return authorization headers"""
    credentials = USER_LOGIN if role == "user" else ADMIN_LOGIN
    res = requests.post(url=f"{BASE_URL}login", json=credentials)
    assert res.status_code == 200, f"Login failed: {res.json()}"
    token = res.json()["session_token"]
    return {"Authorization": token}

@pytest.fixture
def user_headers():
    return login("user")

@pytest.fixture
def admin_headers():
    return login("admin")

@pytest.fixture
def sample_discount_data():
    return {
        "code": f"TEST-DISCOUNT-{uuid.uuid4().hex[:8].upper()}",
        "discount_type": "percentage",
        "discount_value": 15.0,
        "max_uses": 10,
        "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
    }

@pytest.fixture
def created_discount(admin_headers, sample_discount_data):
    res = requests.post(
        url=f"{BASE_URL}discount-codes",
        json=sample_discount_data,
        headers=admin_headers
    )
    assert res.status_code == 201
    return res.json()

@pytest.fixture
def sample_payment_data():
    return {
        "amount": 100.0,
        "session_id": 12345,
        "parking_lot_id": 1,
        "t_data": {
            "amount": 100.0,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "method": "credit_card",
            "issuer": "visa",
            "bank": "test_bank"
        }
    }

# ============================================================================
# DISCOUNT CODE TESTS
# ============================================================================

class TestDiscountCodes:
    def test_create_discount_code_admin(self, admin_headers, sample_discount_data):
        res = requests.post(
            url=f"{BASE_URL}discount-codes",
            json=sample_discount_data,
            headers=admin_headers
        )
        assert res.status_code == 201
        data = res.json()
        assert data["code"] == sample_discount_data["code"]
        assert data["discount_value"] == 15.0

    def test_create_discount_code_user_forbidden(self, user_headers, sample_discount_data):
        res = requests.post(
            url=f"{BASE_URL}discount-codes",
            json=sample_discount_data,
            headers=user_headers
        )
        assert res.status_code == 403

    def test_get_all_discount_codes_admin(self, admin_headers, created_discount):
        res = requests.get(
            url=f"{BASE_URL}discount-codes",
            headers=admin_headers
        )
        assert res.status_code == 200
        codes = [d["code"] for d in res.json()]
        assert created_discount["code"] in codes

    def test_get_discount_by_code_admin(self, admin_headers, created_discount):
        res = requests.get(
            url=f"{BASE_URL}discount-codes/{created_discount['code']}",
            headers=admin_headers
        )
        assert res.status_code == 200
        assert res.json()["code"] == created_discount["code"]

    def test_update_discount_code_admin(self, admin_headers, created_discount):
        update_data = created_discount.copy()
        update_data["discount_value"] = 25.0
        
        res = requests.put(
            url=f"{BASE_URL}discount-codes/{created_discount['code']}",
            json=update_data,
            headers=admin_headers
        )
        assert res.status_code == 200
        assert res.json()["discount_value"] == 25.0

    def test_deactivate_discount_code_admin(self, admin_headers, created_discount):
        res = requests.delete(
            url=f"{BASE_URL}discount-codes/{created_discount['code']}",
            headers=admin_headers
        )
        assert res.status_code == 200
        assert res.json()["active"] is False

# ============================================================================
# PAYMENT WITH DISCOUNT TESTS
# ============================================================================

class TestPaymentWithDiscount:
    def test_payment_with_percentage_discount(self, user_headers, admin_headers, sample_payment_data):
        # 1. Create a 20% discount code
        discount_code = f"SAVE20-{uuid.uuid4().hex[:4].upper()}"
        requests.post(
            url=f"{BASE_URL}discount-codes",
            json={
                "code": discount_code,
                "discount_type": "percentage",
                "discount_value": 20.0,
                "max_uses": 10
            },
            headers=admin_headers
        )
        
        # 2. Make payment with discount
        payment_data = sample_payment_data.copy()
        payment_data["discount_code"] = discount_code
        payment_data["amount"] = 100.0
        
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=payment_data,
            headers=user_headers
        )
        
        assert res.status_code == 201
        data = res.json()
        assert data["discount_applied"] == discount_code
        assert data["original_amount"] == 100.0
        assert data["amount"] == 80.0 # 100 - 20%
        assert data["discount_amount"] == 20.0

    def test_payment_with_fixed_discount(self, user_headers, admin_headers, sample_payment_data):
        # 1. Create a $10 fixed discount code
        discount_code = f"FIX10-{uuid.uuid4().hex[:4].upper()}"
        requests.post(
            url=f"{BASE_URL}discount-codes",
            json={
                "code": discount_code,
                "discount_type": "fixed",
                "discount_value": 10.0,
                "max_uses": 10
            },
            headers=admin_headers
        )
        
        # 2. Make payment with discount
        payment_data = sample_payment_data.copy()
        payment_data["discount_code"] = discount_code
        payment_data["amount"] = 50.0
        
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=payment_data,
            headers=user_headers
        )
        
        assert res.status_code == 201
        data = res.json()
        assert data["discount_applied"] == discount_code
        assert data["amount"] == 40.0 # 50 - 10
        assert data["discount_amount"] == 10.0

    def test_payment_with_invalid_discount(self, user_headers, sample_payment_data):
        payment_data = sample_payment_data.copy()
        payment_data["discount_code"] = "NONEXISTENT"
        
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=payment_data,
            headers=user_headers
        )
        
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]

    def test_payment_with_expired_discount(self, user_headers, admin_headers, sample_payment_data):
        # 1. Create an expired discount code
        discount_code = f"EXPIRED-{uuid.uuid4().hex[:4].upper()}"
        requests.post(
            url=f"{BASE_URL}discount-codes",
            json={
                "code": discount_code,
                "discount_type": "percentage",
                "discount_value": 10.0,
                "max_uses": 10,
                "expires_at": (datetime.now() - timedelta(days=1)).isoformat()
            },
            headers=admin_headers
        )
        
        # 2. Make payment with discount
        payment_data = sample_payment_data.copy()
        payment_data["discount_code"] = discount_code
        
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=payment_data,
            headers=user_headers
        )
        
        assert res.status_code == 400
        assert "expired" in res.json()["detail"]

# ============================================================================
# REFUND TESTS
# ============================================================================

class TestRefunds:
    @pytest.fixture
    def payment_to_refund(self, user_headers, sample_payment_data):
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=sample_payment_data,
            headers=user_headers
        )
        assert res.status_code == 201
        return res.json()

    def test_create_refund_admin(self, admin_headers, payment_to_refund):
        refund_data = {
            "original_transaction_id": payment_to_refund["transaction"],
            "amount": payment_to_refund["amount"] / 2,
            "reason": "Partial refund test"
        }
        
        res = requests.post(
            url=f"{BASE_URL}refunds",
            json=refund_data,
            headers=admin_headers
        )
        
        assert res.status_code == 201
        data = res.json()
        assert data["original_transaction_id"] == payment_to_refund["transaction"]
        assert data["amount"] == payment_to_refund["amount"] / 2
        assert data["status"] == "completed"

    def test_create_refund_user_forbidden(self, user_headers, payment_to_refund):
        refund_data = {
            "original_transaction_id": payment_to_refund["transaction"],
            "amount": payment_to_refund["amount"],
            "reason": "Should fail"
        }
        
        res = requests.post(
            url=f"{BASE_URL}refunds",
            json=refund_data,
            headers=user_headers
        )
        
        assert res.status_code == 403

    def test_create_refund_exceeds_amount(self, admin_headers, payment_to_refund):
        refund_data = {
            "original_transaction_id": payment_to_refund["transaction"],
            "amount": payment_to_refund["amount"] + 1.0,
            "reason": "Exceeds amount"
        }
        
        res = requests.post(
            url=f"{BASE_URL}refunds",
            json=refund_data,
            headers=admin_headers
        )
        
        assert res.status_code == 422
        assert "exceeds remaining refundable amount" in res.json()["detail"]

    def test_get_all_refunds_admin(self, admin_headers, payment_to_refund):
        # Create a refund first
        requests.post(
            url=f"{BASE_URL}refunds",
            json={
                "original_transaction_id": payment_to_refund["transaction"],
                "amount": 1.0,
                "reason": "test"
            },
            headers=admin_headers
        )
        
        res = requests.get(
            url=f"{BASE_URL}refunds",
            headers=admin_headers
        )
        
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_get_user_refunds(self, user_headers, admin_headers, payment_to_refund):
        # 1. Admin creates a refund for the user's payment
        requests.post(
            url=f"{BASE_URL}refunds",
            json={
                "original_transaction_id": payment_to_refund["transaction"],
                "amount": 5.0,
                "reason": "User refund"
            },
            headers=admin_headers
        )
        
        # 2. User gets their refunds
        res = requests.get(
            url=f"{BASE_URL}refunds",
            headers=user_headers
        )
        
        assert res.status_code == 200
        user_refunds = res.json()
        assert any(r["original_transaction_id"] == payment_to_refund["transaction"] for r in user_refunds)

    def test_get_refund_by_id(self, user_headers, admin_headers, payment_to_refund):
        # 1. Admin creates a refund
        create_res = requests.post(
            url=f"{BASE_URL}refunds",
            json={
                "original_transaction_id": payment_to_refund["transaction"],
                "amount": 5.0,
                "reason": "ID test"
            },
            headers=admin_headers
        )
        refund_id = create_res.json()["refund_id"]
        
        # 2. User gets the refund by ID
        res = requests.get(
            url=f"{BASE_URL}refunds/{refund_id}",
            headers=user_headers
        )
        
        assert res.status_code == 200
        assert res.json()["refund_id"] == refund_id

    def test_get_refunds_for_transaction(self, user_headers, admin_headers, payment_to_refund):
        transaction_id = payment_to_refund["transaction"]
        
        # 1. Admin creates a refund
        requests.post(
            url=f"{BASE_URL}refunds",
            json={
                "original_transaction_id": transaction_id,
                "amount": 2.0,
                "reason": "Transaction test"
            },
            headers=admin_headers
        )
        
        # 2. User gets refunds for transaction
        res = requests.get(
            url=f"{BASE_URL}refunds/transaction/{transaction_id}",
            headers=user_headers
        )
        
        assert res.status_code == 200
        assert len(res.json()) >= 1
        assert res.json()[0]["original_transaction_id"] == transaction_id
