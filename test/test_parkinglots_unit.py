import pytest
from services import parking_services
from models.parking_lots_model import ParkingLot, Coordinates, UpdateParkingLot

def test_create_parking_lot(monkeypatch):
    # Set up fake storage
    storage = {}
    def test_save(data):
        storage["data"] = data

    monkeypatch.setattr(
        "services.parking_services.storage_utils.save_parking_lot_data",
        test_save
    )

    dummy_lot = ParkingLot(
        name = "TEST",
        location = "TEST_LOCATION",
        address ="TEST_ADDRESS",
        capacity = 10,
        reserved = 0,
        tariff = 2.50,
        daytariff = 20.00,
        created_at = "2025-12-12",
        coordinates = Coordinates(
            lat = 40.712776,
            lng = -74.005974
        )
    )
    parking_services.create_parking_lot(dummy_lot)

    # Assert data exists in storage
    assert "data" in storage
    # Retrieve latest parking lot in storage
    latest_lot = next(reversed(storage["data"].values()))
    assert latest_lot["name"] == "TEST"
    assert latest_lot["location"] == "TEST_LOCATION"
    assert latest_lot["address"] == "TEST_ADDRESS"
    assert latest_lot["capacity"] == 10
    assert latest_lot["reserved"] == 0
    assert latest_lot["tariff"] == 2.50
    assert latest_lot["daytariff"] == 20.00
    assert latest_lot["created_at"] == "2025-12-12"
    assert latest_lot["coordinates"]["lat"] == 40.712776
    assert latest_lot["coordinates"]["lng"] == -74.005974

def test_update_parking_lot_one_field(monkeypatch):
    storage = {}
    def test_save(data):
        storage["data"] = data
    
    def test_load():
        return storage

    monkeypatch.setattr(
        "services.parking_services.storage_utils.save_parking_lot_data",
        test_save
    )
    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_parking_lot_data",
        test_load
    )

    dummy_lot = ParkingLot(
        name = "TEST",
        location = "TEST_LOCATION",
        address ="TEST_ADDRESS",
        capacity = 10,
        reserved = 0,
        tariff = 2.50,
        daytariff = 20.00,
        created_at = "2025-12-12",
        coordinates = Coordinates(
            lat = 40.712776,
            lng = -74.005974
        )
    )
    # Update parking lot function expects dict,
    # rather than ParkingLot object
    storage["xyz"] = dummy_lot.model_dump()
    key = "xyz"

    dummy_updated_lot = UpdateParkingLot(
        name = "UPDATED_TEST"
    )

    parking_services.update_parking_lot(key, dummy_updated_lot)
    # Assert only name changed
    assert storage["xyz"]["name"] == "UPDATED_TEST"
    assert storage["xyz"]["location"] == "TEST_LOCATION"
    assert storage["xyz"]["address"] == "TEST_ADDRESS"
    assert storage["xyz"]["capacity"] == 10
    assert storage["xyz"]["reserved"] == 0
    assert storage["xyz"]["tariff"] == 2.50
    assert storage["xyz"]["daytariff"] == 20.00
    assert storage["xyz"]["created_at"] == "2025-12-12"
    assert storage["xyz"]["coordinates"]["lat"] == 40.712776
    assert storage["xyz"]["coordinates"]["lng"] == -74.005974

def test_update_parking_lot_all_fields(monkeypatch):
    storage = {}
    def test_save(data):
        storage["data"] = data
    
    def test_load():
        return storage

    monkeypatch.setattr(
        "services.parking_services.storage_utils.save_parking_lot_data",
        test_save
    )
    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_parking_lot_data",
        test_load
    )

    dummy_lot = ParkingLot(
        name = "TEST",
        location = "TEST_LOCATION",
        address ="TEST_ADDRESS",
        capacity = 10,
        reserved = 0,
        tariff = 2.50,
        daytariff = 20.00,
        created_at = "2025-12-12",
        coordinates = Coordinates(
            lat = 40.712776,
            lng = -74.005974
        )
    )
    # Update parking lot function expects dict,
    # rather than ParkingLot object
    storage["xyz"] = dummy_lot.model_dump()
    key = "xyz"

    dummy_updated_lot = UpdateParkingLot(
        name = "UPDATED_TEST",
        location = "UPDATED_TEST_LOCATION",
        address ="UPDATED_TEST_ADDRESS",
        capacity = 20,
        reserved = 10,
        tariff = 5.50,
        daytariff = 30.00,
        created_at = "2024-12-12",
        coordinates = Coordinates(
            lat = 30.712776,
            lng = -40.005974
        )
    )

    parking_services.update_parking_lot(key, dummy_updated_lot)
    # Assert only name changed
    assert storage["xyz"]["name"] == "UPDATED_TEST"
    assert storage["xyz"]["location"] == "UPDATED_TEST_LOCATION"
    assert storage["xyz"]["address"] == "UPDATED_TEST_ADDRESS"
    assert storage["xyz"]["capacity"] == 20
    assert storage["xyz"]["reserved"] == 10
    assert storage["xyz"]["tariff"] == 5.50
    assert storage["xyz"]["daytariff"] == 30.00
    assert storage["xyz"]["created_at"] == "2024-12-12"
    assert storage["xyz"]["coordinates"]["lat"] == 30.712776
    assert storage["xyz"]["coordinates"]["lng"] == -40.005974

def test_delete_parking_lot(monkeypatch):
    storage = {}
    def test_save(data):
        storage["data"] = data
    
    def test_load():
        return storage

    monkeypatch.setattr(
        "services.parking_services.storage_utils.save_parking_lot_data",
        test_save
    )
    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_parking_lot_data",
        test_load
    )

    dummy_lot = ParkingLot(
        name = "TEST",
        location = "TEST_LOCATION",
        address ="TEST_ADDRESS",
        capacity = 10,
        reserved = 0,
        tariff = 2.50,
        daytariff = 20.00,
        created_at = "2025-12-12",
        coordinates = Coordinates(
            lat = 40.712776,
            lng = -74.005974
        )
    )
    # Update parking lot function expects dict,
    # rather than ParkingLot object
    storage["xyz"] = dummy_lot.model_dump()
    key = "xyz"

    parking_services.delete_parking_lot(key)
    assert key not in storage
