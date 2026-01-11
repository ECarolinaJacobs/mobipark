import pytest
import sqlite3
import tempfile
import os

# from pathlib import Path
from fastapi.testclient import TestClient
import uuid
from utils.session_manager import add_session, sessions


@pytest.fixture(autouse=True)
def cleanup_sessions():
    """automatically clean up sessions before and after each test"""
    sessions.clear()  # before test
    yield
    sessions.clear()  # after test


@pytest.fixture(scope="function")
def test_db():
    """create a temporary test database with schema and seed data for hotel manager feauture"""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # create users table
    cursor.execute(
        """
        CREATE TABLE users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        name TEXT,
        email TEXT,
        phone TEXT,
        role TEXT,
        created_at TEXT,
        birth_year INTEGER,
        active INTEGER,
        hash_type TEXT,
        managed_parking_lot_id TEXT
        )
    """
    )
    # create table parking lots
    cursor.execute(
        """
        CREATE TABLE parking_lots (
        id TEXT PRIMARY KEY,
        name TEXT,
        location TEXT,
        address TEXT,
        capacity INTEGER,
        reserved INTEGER,
        tariff REAL,
        daytariff REAL,
        created_at TEXT,
        "coordinates.lat" REAL,
        "coordinates.lng" REAL
        )
    """
    )
    # create table discounts
    cursor.execute(
        """
        CREATE TABLE discounts (
        code TEXT PRIMARY KEY,
        discount_type TEXT,
        discount_value REAL,
        max_uses INTEGER,
        current_uses INTEGER,
        active INTEGER,
        created_at TEXT,
        check_in_date TEXT,
        check_out_date TEXT,
        parking_lot_id TEXT,
        created_by TEXT,
        guest_name TEXT,
        notes TEXT,
        is_hotel_code INTEGER
        )
    """
    )

    # insert test data

    # insert test admin
    # password is admin123
    cursor.execute(
        """
        INSERT INTO users VALUES
        ('admin-test-id', 'admin_test', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIBx.N4F6i',
         'Admin User', 'admin@test.com', '1234567890', 'ADMIN', '2024-01-01',
         NULL, 1, 'bcrypt', NULL)
    """
    )

    # Insert test hotel manager
    # Password is "hotelpass123" hashed with bcrypt
    cursor.execute(
        """
        INSERT INTO users VALUES
        ('hotel-mgr-test-id', 'hotel_mgr_test', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIBx.N4F6i',
         'Hotel Manager Test', 'manager@hotel.com', '0987654321', 'HOTEL_MANAGER',
         '2024-01-01', NULL, 1, 'bcrypt', '1')
    """
    )

    # Insert test regular user
    # Password is "userpass123" hashed with bcrypt
    cursor.execute(
        """
        INSERT INTO users VALUES
        ('user-test-id', 'regular_user', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIBx.N4F6i',
         'Regular User', 'user@test.com', '5555555555', 'USER', '2024-01-01',
         NULL, 1, 'bcrypt', NULL)
    """
    )

    # Insert test parking lots
    cursor.execute(
        """
        INSERT INTO parking_lots (id, name, location, address, capacity, reserved,
                                 tariff, daytariff, created_at, "coordinates.lat", "coordinates.lng")
        VALUES ('1', 'Hotel Royal Parking', 'Amsterdam', 'Dam 1, Amsterdam', 100, 10,
                5.0, 30.0, '2024-01-01', 52.3676, 4.9041)
    """
    )

    cursor.execute(
        """
        INSERT INTO parking_lots (id, name, location, address, capacity, reserved,
                                 tariff, daytariff, created_at, "coordinates.lat", "coordinates.lng")
        VALUES ('2', 'Downtown Parking', 'Amsterdam', 'Leidseplein 5', 50, 5,
                4.0, 25.0, '2024-01-01', 52.3641, 4.8829)
    """
    )

    # Insert a test discount code created by hotel manager
    cursor.execute(
        """
        INSERT INTO discounts VALUES 
        ('EXISTING-CODE', 'percentage', 100.0, 1, 0, 1, '1704067200',
         '2026-01-10', '2026-01-15', '1', 'hotel_mgr_test', 'John Doe',
         'Test guest', 1)
    """
    )

    conn.commit()
    conn.close()

    yield db_path

    # cleanup tries to delete, but doesnt fail if it cant
    try:
        os.unlink(db_path)
    except (OSError, PermissionError):
        pass  # cleaned up by OS temp cleanup


@pytest.fixture
def client(test_db, monkeypatch):
    """creates fastapi test client with test database"""
    monkeypatch.setenv("TEST_DB_PATH", str(test_db))
    monkeypatch.setenv("USE_MOCK_DATA", "false")

    import sys

    if "utils.storage_utils" in sys.modules:
        from utils import storage_utils
        from pathlib import Path

        storage_utils.DB_PATH = Path(test_db)
        storage_utils.use_mock_data = False
    else:
        from utils import storage_utils

        storage_utils.use_mock_data = False

    assert str(storage_utils.DB_PATH) == str(test_db), "DB_PATH not set correctly"

    monkeypatch.setattr(storage_utils, "load_parking_lot_data", storage_utils.load_parking_lot_data_from_db)
    monkeypatch.setattr(storage_utils, "load_user_data", storage_utils.load_user_data_from_db)

    def save_single_user_to_db(user_data):
        storage_utils.insert_single_json_to_db("users", user_data)

    monkeypatch.setattr(storage_utils, "save_user_data", save_single_user_to_db)
    monkeypatch.setattr(storage_utils, "load_discounts_data", storage_utils.load_discounts_data_from_db)
    monkeypatch.setattr(storage_utils, "save_discounts_data", storage_utils.save_discounts_data_to_db)

    import endpoints.hotel_manager_endpoint as hotel_routes

    monkeypatch.setattr(hotel_routes, "load_parking_lot_data", storage_utils.load_parking_lot_data_from_db)
    monkeypatch.setattr(hotel_routes, "get_discount_by_code", storage_utils.get_discount_by_code)
    monkeypatch.setattr(hotel_routes, "save_new_discount_to_db", storage_utils.save_new_discount_to_db)
    monkeypatch.setattr(
        hotel_routes, "load_discounts_data_from_db", storage_utils.load_discounts_data_from_db
    )
    monkeypatch.setattr(
        hotel_routes, "update_existing_discount_in_db", storage_utils.update_existing_discount_in_db
    )

    try:
        import endpoints.auth as auth_routes

        monkeypatch.setattr(auth_routes, "save_user_data", save_single_user_to_db)
        monkeypatch.setattr(auth_routes, "load_user_data", storage_utils.load_user_data_from_db)
    except ImportError:
        pass

    from main import app

    return TestClient(app)


@pytest.fixture
def admin_token(test_db):
    """cretae a session token for admin user"""
    token = str(uuid.uuid4())
    admin_user = {"id": "admin-test-id", "username": "admin_test", "role": "ADMIN", "name": "Admin User"}
    add_session(token, admin_user)
    return token


@pytest.fixture
def hotel_manager_token(test_db):
    """create a session token for hotel manager"""
    token = str(uuid.uuid4())
    hotel_manager = {
        "id": "hotel-mgr-test-id",
        "username": "hotel_mgr_test",
        "role": "HOTEL_MANAGER",
        "managed_parking_lot_id": "1",
        "name": "Hotel Manager Test",
    }
    add_session(token, hotel_manager)
    return token


@pytest.fixture
def user_token(test_db):
    """create a session token for regular user"""
    token = str(uuid.uuid4())
    user = {"id": "user-test-id", "username": "regular_user", "role": "USER", "name": "Regular User"}
    add_session(token, user)
    return token
