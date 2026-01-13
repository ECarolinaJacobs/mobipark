import pytest
from services import parking_services
from models.parking_lots_model import ParkingLot, Coordinates, UpdateParkingLot, ParkingSessionCreate
from models.reservations_model import CreateReservation
from uuid import uuid4
from datetime import datetime

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

def test_start_parking_session(monkeypatch):
    session_user = {
        "username": "testuser",
        "role": "USER"
    }

    lot_storage = {}
    session_storage = {}
    lot_id = "1"
    license_plate = "TEST-PLATE"

    def test_load_lots():
        lot_storage[lot_id] = ParkingLot(
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
        )).model_dump()
        return lot_storage
    
    def test_load_sessions(lot_id):
        return session_storage

    def test_save_session(data, lot_id):
        session_storage["data"] = data

    def test_load_reservations():
        test_reservation = CreateReservation(
            user_id = "1",
            vehicle_id = str(uuid4()),
            start_time = "2026-12-12T10:00",
            end_time = "2026-12-12T12:00",
            parking_lot_id = lot_id
        ).model_dump()
        return test_reservation
    
    def test_find_reservation_by_license_plate(lot_id, license_plate):
        test_reservation = {
            "id": "res-1",
            "user_id": "1",
            "vehicle_id": str(uuid4()),
            "start_time": "2026-12-12T10:00",
            "end_time": "2026-12-12T12:00",
            "parking_lot_id": lot_id,
            "status": "pending"
        }
        return test_reservation

    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_parking_lot_data",
        test_load_lots
    )

    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_parking_session_data",
        test_load_sessions
    )

    monkeypatch.setattr(
        "services.parking_services.storage_utils.save_parking_session_data",
        test_save_session
    )

    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_reservation_data",
        test_load_reservations
    )

    monkeypatch.setattr(
        "services.parking_services.find_reservation_by_license_plate",
        test_find_reservation_by_license_plate
    )

    session_data = ParkingSessionCreate(
        licenseplate = license_plate
    )
    
    parking_services.start_parking_session(lot_id, session_data, session_user)
    assert session_storage["data"]["1"]["licenseplate"] == "TEST-PLATE"

def test_stop_parking_session(monkeypatch):
    session_user = {
        "username": "testuser",
        "role": "USER"
    }
    license_plate = "TEST-PLATE"
    lot_id = "1"
    session_id = "1"
    session_storage = {}
    lot_storage = {}

    def test_load_lots():
        lot_storage[lot_id] = ParkingLot(
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
        )).model_dump()
        return lot_storage
    
    def test_load_sessions(lot_id):
        session_storage[session_id] = {
            "licenseplate": "TEST-PLATE",
            "started": "2026-12-12T10:00",
            "stopped": None,
            "user": "testuser"
        }
        return session_storage
    
    def test_find_reservation_by_license_plate(lot_id, license_plate):
        test_reservation = {
            "id": "res-1",
            "user_id": "1",
            "vehicle_id": str(uuid4()),
            "start_time": "2026-12-12T10:00",
            "end_time": "2026-12-12T12:00",
            "parking_lot_id": lot_id,
            "status": "pending"
        }
        return test_reservation
    
    def test_calculate_price(lot, session_id, data):
        return (1, 1, 0)
    
    def test_find_session_by_plate(lot_id, license_plate):
        return session_id
        
    def test_update_reservation_end_time(reservation_id, end_time):
        return None

    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_parking_lot_data",
        test_load_lots
    )

    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_parking_session_data",
        test_load_sessions
    )

    monkeypatch.setattr(
        "services.parking_services.find_reservation_by_license_plate",
        test_find_reservation_by_license_plate
    )

    monkeypatch.setattr(
        "services.parking_services.calculate_price",
        test_calculate_price
    )

    monkeypatch.setattr(
        "services.parking_services.storage_utils.find_parking_session_id_by_plate",
        test_find_session_by_plate
    )

    monkeypatch.setattr(
        "services.parking_services.update_reservation_end_time",
        test_update_reservation_end_time
    )

    session_data = ParkingSessionCreate(
        licenseplate = license_plate
    )

    parking_services.stop_parking_session(lot_id, session_data, session_user)
    assert session_storage[session_id]["licenseplate"] == license_plate
    assert session_storage[session_id]["stopped"] == datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def test_update_parking_session(monkeypatch):
    lot_storage = {}
    session_storage = {}
    lot_id = "1"
    session_id = "1"
    license_plate = "TEST-PLATE-UPDATED"

    def test_load_lots():
        lot_storage[lot_id] = ParkingLot(
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
        )).model_dump()
        return lot_storage
    
    def test_load_sessions(lot_id):
        session_storage[session_id] = {
            "licenseplate": "TEST-PLATE",
            "started": "2026-12-12T10:00",
            "stopped": None,
            "user": "testuser"
        }
        return session_storage
    
    def test_save_sessions(session, lot_id):
        session_storage.update(session)
    
    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_parking_lot_data",
        test_load_lots
    )

    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_parking_session_data",
        test_load_sessions
    )

    monkeypatch.setattr(
        "services.parking_services.storage_utils.save_parking_session_data",
        test_save_sessions
    )

    updated_session = ParkingSessionCreate(
        licenseplate = license_plate
    )

    parking_services.update_parking_session(lot_id, session_id, updated_session)
    assert session_storage[session_id]["licenseplate"] == license_plate

def test_delete_parking_session(monkeypatch):
    session_storage = {}
    session_id = "1"
    lot_id = "1"

    def test_load_sessions(lot_id):
        session_storage[session_id] = {
            "licenseplate": "TEST-PLATE",
            "started": "2026-12-12T10:00",
            "stopped": None,
            "user": "testuser"
        }
        return session_storage
    
    def test_save_sessions(session, lot_id):
        session_storage.update(session)

    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_parking_session_data",
        test_load_sessions
    )

    monkeypatch.setattr(
        "services.parking_services.storage_utils.save_parking_session_data",
        test_save_sessions
    )

    parking_services.delete_parking_session(session_id, lot_id)
    assert session_id not in session_storage