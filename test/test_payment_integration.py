import pytest
import requests
from datetime import datetime
import uuid
from urllib.parse import quote  # <--- NEW IMPORT

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


# ============================================================================
# AUTHENTICATION HELPER AND FIXTURES
# ============================================================================

def login(role: str = "user"):
    """Login and return authorization headers"""
    credentials = USER_LOGIN if role == "user" else ADMIN_LOGIN
    res = requests.post(url=f"{BASE_URL}login", json=credentials)
    assert res.status_code == 200, f"Login failed: {res.json()}"
    token = res.json()["session_token"]
    return {"Authorization": token}


@pytest.fixture
def user_headers():
    """Get authentication headers for regular user"""
    return login("user")


@pytest.fixture
def admin_headers():
    """Get authentication headers for admin user"""
    return login("admin")


# ============================================================================
# PAYMENT DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_payment_data():
    """Sample payment data for POST requests"""
    return {
        "amount": 100.50,
        "session_id": 14532,
        "parking_lot_id": 1500,
        "t_data": {
            "amount": 100.50,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "method": "ideal",
            "issuer": "TJ1SV6ZN",
            "bank": "ASN"
        }
    }


@pytest.fixture
def created_payment(user_headers, sample_payment_data):
    """Create a payment and return it"""
    res = requests.post(
        url=f"{BASE_URL}payments",
        json=sample_payment_data,
        headers=user_headers
    )
    assert res.status_code == 201
    return res.json()


@pytest.fixture
def multiple_payments(user_headers, sample_payment_data):
    """Create multiple payments for the same user"""
    payments = []
    for i in range(3):
        data = sample_payment_data.copy()
        data["amount"] = 50.00 + (i * 10)
        data["session_id"] = 14532 + i
        data["t_data"] = {
            "amount": 50.00 + (i * 10),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "method": "ideal",
            "issuer": f"ISSUER_{i}",
            "bank": "ASN"
        }
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=data,
            headers=user_headers
        )
        assert res.status_code == 201
        payments.append(res.json())
    return payments


@pytest.fixture
def admin_payment(admin_headers, sample_payment_data):
    """Create a payment as admin"""
    data = sample_payment_data.copy()
    data["session_id"] = 99999
    res = requests.post(
        url=f"{BASE_URL}payments",
        json=data,
        headers=admin_headers
    )
    assert res.status_code == 201
    return res.json()


# ============================================================================
# POST TESTS (10 tests)
# ============================================================================

class TestPostPayments:
    
    def test_post_payment_success(self, user_headers, sample_payment_data):
        """Test successful payment creation with all required fields"""
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=sample_payment_data,
            headers=user_headers
        )
        
        assert res.status_code == 201
        payment = res.json()
        
        # Verify all fields are present
        assert "transaction" in payment
        assert "hash" in payment
        assert "initiator" in payment
        assert "created_at" in payment
        assert "completed" in payment
        assert payment["amount"] == 100.50
        assert payment["session_id"] == "14532"
        assert payment["parking_lot_id"] == "1500"
        assert payment["t_data"]["method"] == "ideal"
    
    def test_post_payment_as_admin(self, admin_headers, sample_payment_data):
        """Test admin can create payments"""
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=sample_payment_data,
            headers=admin_headers
        )
        
        assert res.status_code == 201
        payment = res.json()
        assert payment["initiator"] == "admin"
    
    def test_post_payment_missing_t_data(self, user_headers):
        """Test payment creation fails without t_data"""
        data = {
            "amount": 100.50,
            "session_id": 14532,
            "parking_lot_id": 1500
            # Missing t_data
        }
        
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=data,
            headers=user_headers
        )
        
        assert res.status_code == 422
    
    def test_post_payment_negative_amount(self, user_headers):
        """Test payment creation fails with negative amount"""
        data = {
            "amount": -50.00,
            "session_id": 14532,
            "parking_lot_id": 1500,
            "t_data": {
                "amount": -50.00,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "method": "ideal",
                "issuer": "TJ1SV6ZN",
                "bank": "ASN"
            }
        }
        
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=data,
            headers=user_headers
        )
        
        assert res.status_code == 422
    
    
    def test_post_payment_without_auth(self, sample_payment_data):
        """Test payment creation fails without authentication"""
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=sample_payment_data
            # No headers
        )
        
        assert res.status_code == 401
    
    def test_post_payment_with_invalid_token(self, sample_payment_data):
        """Test payment creation fails with invalid token"""
        invalid_headers = {"Authorization": "invalid-token-12345"}
        
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=sample_payment_data,
            headers=invalid_headers
        )
        
        assert res.status_code == 401
    
    def test_post_payment_different_methods(self, user_headers):
        """Test creating payments with different payment methods"""
        methods = ["ideal", "creditcard", "paypal", "bancontact"]
        
        for i, method in enumerate(methods):
            data = {
                "amount": 75.00,
                "session_id": 20000 + i,
                "parking_lot_id": 1500,
                "t_data": {
                    "amount": 75.00,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "method": method,
                    "issuer": "TEST_ISSUER",
                    "bank": "TEST_BANK"
                }
            }
            
            res = requests.post(
                url=f"{BASE_URL}payments",
                json=data,
                headers=user_headers
            )
            
            assert res.status_code == 201
            payment = res.json()
            assert payment["t_data"]["method"] == method
    
    def test_post_payment_large_amount(self, user_headers):
        """Test creating payment with large amount"""
        data = {
            "amount": 9999.99,
            "session_id": 30000,
            "parking_lot_id": 1500,
            "t_data": {
                "amount": 9999.99,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "method": "creditcard",
                "issuer": "VISA",
                "bank": "ING"
            }
        }
        
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=data,
            headers=user_headers
        )
        
        assert res.status_code == 201
        payment = res.json()
        assert payment["amount"] == 9999.99


# ============================================================================
# GET TESTS (8 tests)
# ============================================================================

class TestGetPayments:
    
    def test_get_all_payments_as_user(self, user_headers, multiple_payments):
        """Test user can only see their own payments"""
        res = requests.get(
            url=f"{BASE_URL}payments",
            headers=user_headers
        )
        
        assert res.status_code == 200
        payments = res.json()
        
        # User should see at least their 3 created payments
        assert len(payments) >= 3
        
        # Verify these are their payments
        created_transaction_ids = [p["transaction"] for p in multiple_payments]
        returned_transaction_ids = [p["transaction"] for p in payments]
        
        for txn_id in created_transaction_ids:
            assert txn_id in returned_transaction_ids
        
        # All payments should belong to the user
        for payment in payments:
            assert payment["initiator"] == "test"
    
    def test_get_all_payments_as_admin(self, admin_headers, user_headers, sample_payment_data):
        """Test admin can see all payments from all users"""
        # Create a payment as a regular user, separate from any fixtures
        user_payment = requests.post(
            url=f"{BASE_URL}payments",
            json=sample_payment_data,
            headers=user_headers
        )
        assert user_payment.status_code == 201
        user_txn = user_payment.json()["transaction"]
        
        # Admin gets all payments
        res = requests.get(
            url=f"{BASE_URL}payments",
            headers=admin_headers
        )
        
        assert res.status_code == 200
        payments = res.json()
        
        # Admin should see payments from different users
        assert len(payments) > 0
        
        # Verify admin can see the specific user's payment
        all_txns = [p["transaction"] for p in payments]
        assert user_txn in all_txns
    
    def test_get_payment_by_id_owner(self, user_headers, created_payment):
        """Test user can get their own payment by ID"""
        transaction_id = created_payment["transaction"]
        
        # FIX: URL-encode the transaction_id
        res = requests.get(
            url=f"{BASE_URL}payments/{quote(transaction_id)}",
            headers=user_headers
        )
        
        assert res.status_code == 200
        payment = res.json()
        assert payment["transaction"] == transaction_id
        assert payment["amount"] == created_payment["amount"]
        assert payment["initiator"] == "test"
    
    def test_get_payment_by_id_admin(self, admin_headers, created_payment):
        """Test admin can get any payment by ID"""
        transaction_id = created_payment["transaction"]
        
        # FIX: URL-encode the transaction_id
        res = requests.get(
            url=f"{BASE_URL}payments/{quote(transaction_id)}",
            headers=admin_headers
        )
        
        assert res.status_code == 200
        payment = res.json()
        assert payment["transaction"] == transaction_id
    
    def test_get_payment_by_id_not_owner(self, user_headers, admin_payment):
        """Test user cannot get another user's payment"""
        transaction_id = admin_payment["transaction"]
        
        # FIX: URL-encode the transaction_id
        res = requests.get(
            url=f"{BASE_URL}payments/{quote(transaction_id)}",
            headers=user_headers
        )
        
        assert res.status_code == 403
    
    def test_get_nonexistent_payment(self, user_headers):
        """Test getting non-existent payment returns 404"""
        res = requests.get(
            url=f"{BASE_URL}payments/nonexistent-transaction-id-xyz",
            headers=user_headers
        )
        
        assert res.status_code == 404
    
    def test_get_payments_without_auth(self):
        """Test getting payments without authentication fails"""
        res = requests.get(url=f"{BASE_URL}payments")
        
        assert res.status_code == 401
    
    def test_get_payment_by_id_without_auth(self, created_payment):
        """Test getting specific payment without auth fails"""
        transaction_id = created_payment["transaction"]
        
        # FIX: URL-encode the transaction_id
        res = requests.get(
            url=f"{BASE_URL}payments/{quote(transaction_id)}"
        )
        
        assert res.status_code == 401


# ============================================================================
# PUT TESTS (7 tests)
# ============================================================================

class TestPutPayments:
    
    def test_update_payment_as_admin(self, admin_headers, created_payment):
        """Test admin can update any payment"""
        transaction_id = created_payment["transaction"]
        
        update_data = {
            "amount": 200.00,
            "t_data": {
                "amount": 200.00,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "method": "creditcard",
                "issuer": "VISA",
                "bank": "ING"
            }
        }
        
        # FIX: URL-encode the transaction_id
        res = requests.put(
            url=f"{BASE_URL}payments/{quote(transaction_id)}",
            json=update_data,
            headers=admin_headers
        )
        
        assert res.status_code == 200
        updated = res.json()
        assert updated["amount"] == 200.00
        assert updated["t_data"]["method"] == "creditcard"
        assert updated["t_data"]["bank"] == "ING"
    
    def test_update_payment_as_user_forbidden(self, user_headers, created_payment):
        """Test regular user cannot update payments"""
        transaction_id = created_payment["transaction"]
        
        update_data = {"amount": 150.00}
        
        # FIX: URL-encode the transaction_id
        res = requests.put(
            url=f"{BASE_URL}payments/{quote(transaction_id)}",
            json=update_data,
            headers=user_headers
        )
        
        assert res.status_code == 403
    
    
    def test_update_nonexistent_payment(self, admin_headers):
        """Test updating non-existent payment returns 404"""
        update_data = {"amount": 150.00}
        
        res = requests.put(
            url=f"{BASE_URL}payments/nonexistent-id-xyz",
            json=update_data,
            headers=admin_headers
        )
        
        assert res.status_code == 404
    
    def test_update_payment_with_invalid_data(self, admin_headers, created_payment):
        """Test updating payment with invalid data fails validation"""
        transaction_id = created_payment["transaction"]
        
        update_data = {
            "amount": -100.00,  # Negative amount
            "t_data": {
                "amount": -100.00,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "method": "ideal",
                "issuer": "TEST",
                "bank": "TEST"
            }
        }
        
        # FIX: URL-encode the transaction_id
        res = requests.put(
            url=f"{BASE_URL}payments/{quote(transaction_id)}",
            json=update_data,
            headers=admin_headers
        )
        
        assert res.status_code == 422
    
    def test_update_payment_without_auth(self, created_payment):
        """Test updating payment without auth fails"""
        transaction_id = created_payment["transaction"]
        
        update_data = {"amount": 150.00}
        
        # FIX: URL-encode the transaction_id
        res = requests.put(
            url=f"{BASE_URL}payments/{quote(transaction_id)}",
            json=update_data
        )
        
        assert res.status_code == 401
    
    def test_update_only_t_data(self, admin_headers, created_payment):
        """Test updating only transaction data"""
        transaction_id = created_payment["transaction"]
        original_amount = created_payment["amount"]
        
        update_data = {
            "t_data": {
                "amount": original_amount,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "method": "paypal",
                "issuer": "PAYPAL_ID",
                "bank": "PAYPAL"
            }
        }
        
        # FIX: URL-encode the transaction_id
        res = requests.put(
            url=f"{BASE_URL}payments/{quote(transaction_id)}",
            json=update_data,
            headers=admin_headers
        )
        
        assert res.status_code == 200
        updated = res.json()
        assert updated["amount"] == original_amount  # Unchanged
        assert updated["t_data"]["method"] == "paypal"  # Changed
        assert updated["t_data"]["bank"] == "PAYPAL"  # Changed