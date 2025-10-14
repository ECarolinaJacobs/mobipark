import pytest
import requests
from datetime import datetime
import uuid
from hashlib import md5


def generate_random_hash():
    """Generate a random MD5 hash for testing purposes"""
    return md5(str(uuid.uuid4()).encode("utf-8")).hexdigest()


BASE_URL = "http://localhost:8000/"

USER_LOGIN = {
    "username": "test",
    "password": "test",
}

ADMIN_LOGIN = {
    "username": "admin",
    "password": "admin",
}


# Fixtures and Helpers
@pytest.fixture
def user_headers():
    """Get authentication headers for regular user"""
    return login("user")


@pytest.fixture
def admin_headers():
    """Get authentication headers for admin user"""
    return login("admin")


@pytest.fixture
def sample_payment_data(user_headers):
    """Sample payment data for POST/PUT requests with all required fields"""
    return {
        "transaction": generate_random_hash(),
        "amount": 100.50,
        "initiator": "test",
        "hash": generate_random_hash(),
        "t_data": {
            "amount": 100.50,
            "date": datetime.now().isoformat(),
            "method": "credit_card",
            "issuer": "Visa",
            "bank": "Chase",
        },
    }


@pytest.fixture
def sample_payment_data_amount_negative(user_headers):
    """Sample payment data for POST/PUT requests with all required fields and amount is zero"""
    return {
        "transaction": generate_random_hash(),
        "amount": -20,
        "initiator": "test",
        "hash": generate_random_hash(),
        "t_data": {
            "amount": 0.0,
            "date": datetime.now().isoformat(),
            "method": "credit_card",
            "issuer": "Visa",
            "bank": "Chase",
        },
    }


@pytest.fixture
def sample_payment_data_no_transaction_id():
    """Sample payment data missing transaction ID"""
    return {
        "amount": 100.50,
        "initiator": "test",
        "hash": generate_random_hash(),
        "t_data": {
            "amount": 100.50,
            "date": datetime.now().isoformat(),
            "method": "credit_card",
            "issuer": "Visa",
            "bank": "Chase",
        },
    }


@pytest.fixture
def sample_payment_data_no_validation_hash():
    """Sample payment data missing validation hash"""
    return {
        "transaction": generate_random_hash(),
        "amount": 100.50,
        "initiator": "test",
        "t_data": {
            "amount": 100.50,
            "date": datetime.now().isoformat(),
            "method": "credit_card",
            "issuer": "Visa",
            "bank": "Chase",
        },
    }


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for nested objects"""
    return {
        "amount": 250.75,
        "date": datetime.now().isoformat(),
        "method": "debit_card",
        "issuer": "Mastercard",
        "bank": "Bank of America",
    }


def login(role: str = "user"):
    """Login and return authorization headers"""
    credentials = USER_LOGIN if role == "user" else ADMIN_LOGIN
    res = requests.post(url=f"{BASE_URL}login", json=credentials)
    token = res.json()["session_token"]
    return {"Authorization": token}


class TestGetPayments:
    """Test GET endpoints for payments"""

    def test_get_own_payments_authenticated_user(self, user_headers):
        """User can retrieve their own payments"""
        res = requests.get(url=f"{BASE_URL}payments", headers=user_headers)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_get_payments_unauthenticated(self):
        """Unauthenticated request should fail"""
        res = requests.get(
            url=f"{BASE_URL}payments", headers={"Authorization": "invalid_token"}
        )
        assert res.status_code == 401

    def test_get_all_payments_as_user(self, user_headers):
        """Regular user cannot access all payments"""
        res = requests.get(url=f"{BASE_URL}payments/", headers=user_headers)
        assert res.status_code == 403

    def test_get_other_user_payment(self, user_headers):
        """User cannot access another user's payment"""
        fake_id = str(uuid.uuid4())
        res = requests.get(url=f"{BASE_URL}payments/{fake_id}", headers=user_headers)
        assert res.status_code in [403, 404]

    def test_get_all_payments_as_admin(self, admin_headers):
        """Admin can retrieve all payments"""
        res = requests.get(url=f"{BASE_URL}payments/", headers=admin_headers)
        assert res.status_code == 200
        assert len(res.json()) > 100

    def test_get_specific_payment_exists(self, admin_headers):
        """Admin can retrieve specific payment by ID"""
        res = requests.get(url=f"{BASE_URL}payments/", headers=admin_headers)
        payments = res.json()
        assert len(payments) != 0
        if payments:
            payment_id = payments[0]["transaction"]
            res = requests.get(
                url=f"{BASE_URL}payments/{payment_id}", headers=admin_headers
            )
            assert res.status_code == 200

    def test_get_payment_not_exists(self, admin_headers):
        """Getting non-existent payment returns 404"""
        fake_id = str(uuid.uuid4())
        res = requests.get(url=f"{BASE_URL}payments/{fake_id}", headers=admin_headers)
        assert res.status_code == 404


class TestPostPayments:
    """Test POST endpoints for payments"""

    def test_post_payment_without_transaction_id(
        self, user_headers, sample_payment_data_no_transaction_id
    ):
        """Trying to add payment without transaction field"""
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=sample_payment_data_no_transaction_id,
            headers=user_headers,
        )
        assert res.status_code in [400, 422]

    def test_post_payment_without_validation_hash(
        self, user_headers, sample_payment_data_no_validation_hash
    ):
        """Trying to add payment without validation field"""
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=sample_payment_data_no_validation_hash,
            headers=user_headers,
        )
        assert res.status_code in [400, 422]

    def test_post_payment_amount_is_negative(
        self, user_headers, sample_payment_data_amount_negative
    ):
        """Trying to add payment where amount is negative"""
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=sample_payment_data_amount_negative,
            headers=user_headers,
        )
        assert res.status_code in [400, 422]

    def test_post_authenticated_payment_with_all_required_fields(
        self, user_headers, sample_payment_data
    ):
        """Trying to add payment with authenticated user"""
        res = requests.post(
            url=f"{BASE_URL}payments", json=sample_payment_data, headers=user_headers
        )
        assert res.status_code == 201

    def test_post_unauthenticated_payment_with_all_required_fields(
        self, user_headers, sample_payment_data
    ):
        """Trying to add payment with unauthenticated user"""
        res = requests.post(
            url=f"{BASE_URL}payments",
            json=sample_payment_data,
            headers={"Authorization": "false_auth"},
        )
        assert res.status_code == 401

    def test_post_payment_refund_user_with_all_required_fields(
        self, user_headers, sample_payment_data
    ):
        """Trying to add a refund with authenticated user"""
        res = requests.post(
            url=f"{BASE_URL}refund", json=sample_payment_data, headers=user_headers
        )
        assert res.status_code == 403

    def test_post_payment_refund_admin_with_all_required_fields(
        self, admin_headers, sample_payment_data
    ):
        """Trying to add a refund with authenticated admin"""
        res = requests.post(
            url=f"{BASE_URL}refund", json=sample_payment_data, headers=admin_headers
        )
        assert res.status_code in [200, 201]


class TestPutPayments:
    """Test PUT endpoints for updating payments"""

    def test_update_own_payment(self, user_headers, sample_payment_data):
        """User can update their own payment"""
        create_res = requests.post(
            url=f"{BASE_URL}payments", headers=user_headers, json=sample_payment_data
        )
        payment_id = create_res.json()["transaction"]

        updated_data = sample_payment_data.copy()
        updated_data["amount"] = 200.00
        res = requests.put(
            url=f"{BASE_URL}payments/{payment_id}",
            headers=user_headers,
            json=updated_data,
        )
        assert res.status_code == 200
        assert res.json()["amount"] == 200.00

    def test_update_payment_unauthenticated(self, sample_payment_data):
        """Unauthenticated user cannot update payment"""
        fake_id = str(uuid.uuid4())
        res = requests.put(
            url=f"{BASE_URL}payments/{fake_id}",
            headers={"Authorization": "invalid_token"},
            json=sample_payment_data,
        )
        assert res.status_code == 401

    def test_update_nonexistent_payment(self, user_headers, sample_payment_data):
        """Updating non-existent payment returns 404"""
        fake_id = str(uuid.uuid4())
        res = requests.put(
            url=f"{BASE_URL}payments/{fake_id}",
            headers=user_headers,
            json=sample_payment_data,
        )
        assert res.status_code == 404

    def test_update_payment_missing_validation_hash(
        self, user_headers, sample_payment_data, sample_payment_data_no_validation_hash
    ):
        """Update fails without validation hash"""
        create_res = requests.post(
            url=f"{BASE_URL}payments", headers=user_headers, json=sample_payment_data
        )
        payment_id = create_res.json()["transaction"]

        res = requests.put(
            url=f"{BASE_URL}payments/{payment_id}",
            headers=user_headers,
            json=sample_payment_data_no_validation_hash,
        )
        assert res.status_code == 422

    def test_update_payment_missing_amount(self, user_headers, sample_payment_data):
        """Update fails without required amount field"""
        create_res = requests.post(
            url=f"{BASE_URL}payments", headers=user_headers, json=sample_payment_data
        )
        payment_id = create_res.json()["transaction"]

        incomplete_data = {
            "transaction": payment_id,
            "initiator": "test",
            "hash": generate_random_hash(),
        }
        res = requests.put(
            url=f"{BASE_URL}payments/{payment_id}",
            headers=user_headers,
            json=incomplete_data,
        )
        assert res.status_code == 422

    def test_update_payment_missing_initiator(self, user_headers, sample_payment_data):
        """Update fails without required initiator field"""
        create_res = requests.post(
            url=f"{BASE_URL}payments", headers=user_headers, json=sample_payment_data
        )
        payment_id = create_res.json()["transaction"]

        incomplete_data = {
            "transaction": payment_id,
            "amount": 150.0,
            "hash": generate_random_hash(),
        }
        res = requests.put(
            url=f"{BASE_URL}payments/{payment_id}",
            headers=user_headers,
            json=incomplete_data,
        )
        assert res.status_code == 422

    def test_update_payment_mark_completed(self, user_headers, sample_payment_data):
        """Payment can be marked as completed"""
        create_res = requests.post(
            url=f"{BASE_URL}payments", headers=user_headers, json=sample_payment_data
        )
        payment_id = create_res.json()["transaction"]

        updated_data = sample_payment_data.copy()
        updated_data["completed"] = datetime.now().isoformat()
        res = requests.put(
            url=f"{BASE_URL}payments/{payment_id}",
            headers=user_headers,
            json=updated_data,
        )
        assert res.status_code == 200
        assert res.json()["completed"] is not None

    def test_update_transaction_data(self, user_headers, sample_payment_data):
        """Transaction data can be updated"""
        create_res = requests.post(
            url=f"{BASE_URL}payments", headers=user_headers, json=sample_payment_data
        )
        payment_id = create_res.json()["transaction"]

        updated_data = sample_payment_data.copy()
        updated_data["t_data"]["method"] = "wire_transfer"
        updated_data["t_data"]["bank"] = "Wells Fargo"
        res = requests.put(
            url=f"{BASE_URL}payments/{payment_id}",
            headers=user_headers,
            json=updated_data,
        )
        assert res.status_code == 200
        assert res.json()["t_data"]["method"] == "wire_transfer"
        assert res.json()["t_data"]["bank"] == "Wells Fargo"

    def test_update_other_user_payment(
        self, user_headers, admin_headers, sample_payment_data
    ):
        """User cannot update another user's payment"""
        create_res = requests.post(
            url=f"{BASE_URL}payments", headers=admin_headers, json=sample_payment_data
        )
        payment_id = create_res.json()["transaction"]

        updated_data = sample_payment_data.copy()
        updated_data["amount"] = 999.99
        res = requests.put(
            url=f"{BASE_URL}payments/{payment_id}",
            headers=user_headers,
            json=updated_data,
        )
        assert res.status_code == 403

    def test_admin_can_update_any_payment(
        self, user_headers, admin_headers, sample_payment_data
    ):
        """Admin can update any payment"""
        create_res = requests.post(
            url=f"{BASE_URL}payments", headers=user_headers, json=sample_payment_data
        )
        payment_id = create_res.json()["transaction"]

        updated_data = sample_payment_data.copy()
        updated_data["amount"] = 500.00
        res = requests.put(
            url=f"{BASE_URL}payments/{payment_id}",
            headers=admin_headers,
            json=updated_data,
        )
        assert res.status_code == 200
        assert res.json()["amount"] == 500.00

    def test_update_payment_invalid_data_types(self, user_headers, sample_payment_data):
        """Update fails with invalid data types"""
        create_res = requests.post(
            url=f"{BASE_URL}payments", headers=user_headers, json=sample_payment_data
        )
        payment_id = create_res.json()["transaction"]

        invalid_data = {
            "transaction": payment_id,
            "amount": "not_a_number",
            "initiator": "test",
            "hash": generate_random_hash(),
        }
        res = requests.put(
            url=f"{BASE_URL}payments/{payment_id}",
            headers=user_headers,
            json=invalid_data,
        )
        assert res.status_code == 422

    def test_update_payment_negative_amount(self, user_headers, sample_payment_data):
        """Update fails with negative amount"""
        create_res = requests.post(
            url=f"{BASE_URL}payments", headers=user_headers, json=sample_payment_data
        )
        payment_id = create_res.json()["transaction"]

        updated_data = sample_payment_data.copy()
        updated_data["amount"] = -100.0
        res = requests.put(
            url=f"{BASE_URL}payments/{payment_id}",
            headers=user_headers,
            json=updated_data,
        )
        assert res.status_code in [400, 422]

    def test_update_payment_empty_payload(self, user_headers, sample_payment_data):
        """Update fails with empty payload"""
        create_res = requests.post(
            url=f"{BASE_URL}payments", headers=user_headers, json=sample_payment_data
        )
        payment_id = create_res.json()["transaction"]

        res = requests.put(
            url=f"{BASE_URL}payments/{payment_id}", headers=user_headers, json={}
        )
        assert res.status_code == 422
