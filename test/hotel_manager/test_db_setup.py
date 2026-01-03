import pytest
from utils.storage_utils import (
    load_user_data_from_db,
    load_parking_lot_data_from_db,
    load_discounts_data_from_db,
)


def test_db_fixture_creates_users(client):
    """verify test database had users"""
    users = load_user_data_from_db()
    assert len(users) >= 3
    assert any(u["username"] == "admin_test" for u in users)
    assert any(u["username"] == "hotel_mgr_test" for u in users)
    assert any(u["username"] == "regular_user" for u in users)


def test_db_fixture_creates_parking_lots(client):
    """verify test database has parking lots"""
    parking_lots = load_parking_lot_data_from_db()
    assert len(parking_lots) >= 2
    lot_1 = next((lot for lot in parking_lots if lot.get("id") == "1"), None)
    assert lot_1 is not None
    assert lot_1["name"] == "Hotel Royal Parking"


def test_db_fixture_creates_discount_codes(client):
    """verify test database had discount codes"""
    discounts = load_discounts_data_from_db()
    assert len(discounts) >= 1
    existing_code = next((d for d in discounts if d["code"] == "EXISTING-CODE"), None)
    assert existing_code is not None
    assert existing_code["created_by"] == "hotel_mgr_test"
    assert existing_code["is_hotel_code"] == 1


def test_admin_token_fixture_works(client, admin_token):
    """verify admin token fixture works"""
    response = client.get("/parking-lots/", headers={"Authorization": admin_token})
    assert response.status_code == 200


def test_hotel_manager_token_fixture_works(client, hotel_manager_token):
    """verify hotel manager token fixture works"""
    response = client.get(
        "/hotel-manager/managed-parking-lot", headers={"Authorization": hotel_manager_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "1"


def test_user_token_fixture_works(client, user_token):
    """verify user token fixture works"""
    response = client.get("/parking-lots/", headers={"Authorization": user_token})
    assert response.status_code == 200
