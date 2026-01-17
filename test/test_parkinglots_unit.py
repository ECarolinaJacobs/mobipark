import pytest
from services import parking_services
from models.parking_lots_model import ParkingLot, Coordinates, UpdateParkingLot, ParkingSessionCreate
from models.reservations_model import CreateReservation
from uuid import uuid4
from datetime import datetime

def test_create_parking_lot(monkeypatch):
    storage = []
    def test_save(data):
        storage.clear()
        storage.extend(data)
    
    def test_load():
        return storage.copy()

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
    
    session_user = {"username": "testuser", "role": "ADMIN"}
    parking_services.create_parking_lot(dummy_lot, session_user)

    assert len(storage) > 0
    latest_lot = storage[-1]
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
    storage = []
    def test_save(data):
        storage.clear()
        storage.extend(data)
    
    def test_load():
        return storage.copy()

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
    
    key = "999999"
    storage.append({
        "id": key,
        **dummy_lot.model_dump()
    })

    dummy_updated_lot = UpdateParkingLot(
        name = "UPDATED_TEST"
    )

    parking_services.update_parking_lot(key, dummy_updated_lot)
    updated_lot = storage[0]
    # Assert only name changed
    assert updated_lot["name"] == "UPDATED_TEST"
    assert updated_lot["location"] == "TEST_LOCATION"
    assert updated_lot["address"] == "TEST_ADDRESS"
    assert updated_lot["capacity"] == 10
    assert updated_lot["reserved"] == 0
    assert updated_lot["tariff"] == 2.50
    assert updated_lot["daytariff"] == 20.00
    assert updated_lot["created_at"] == "2025-12-12"
    assert updated_lot["coordinates"]["lat"] == 40.712776
    assert updated_lot["coordinates"]["lng"] == -74.005974

def test_update_parking_lot_all_fields(monkeypatch):
    storage = []
    def test_save(data):
        storage.clear()
        storage.extend(data)
    
    def test_load():
        return storage.copy()
    
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
    
    key = "999999"
    storage.append({
        "id": key,
        **dummy_lot.model_dump()
    })

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
    updated_lot = storage[0]

    assert updated_lot["name"] == "UPDATED_TEST"
    assert updated_lot["location"] == "UPDATED_TEST_LOCATION"
    assert updated_lot["address"] == "UPDATED_TEST_ADDRESS"
    assert updated_lot["capacity"] == 20
    assert updated_lot["reserved"] == 10
    assert updated_lot["tariff"] == 5.50
    assert updated_lot["daytariff"] == 30.00
    assert updated_lot["created_at"] == "2024-12-12"
    assert updated_lot["coordinates"]["lat"] == 30.712776
    assert updated_lot["coordinates"]["lng"] == -40.005974

def test_delete_parking_lot(monkeypatch):
    storage = []
    def test_save(data):
        storage.clear()
        storage.extend(data)
    
    def test_load():
        return storage.copy()

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
    
    key = "99999"
    storage.append({
        "id": key,
        **dummy_lot.model_dump()
    })

    parking_services.delete_parking_lot(key)
    assert not any(lot.get("id") == key for lot in storage)

def test_start_parking_session(monkeypatch):
    session_user = {
        "username": "testuser",
        "role": "USER"
    }

    lot_storage = []
    session_storage = []
    lot_id = "999999"
    license_plate = "TEST-PLATE"

    def test_load_lots():
        return lot_storage.copy()

    def test_load_sessions():
        return session_storage.copy()

    def test_save_session(data):
        session_storage.clear()
        session_storage.extend(data)
    
    def test_save_lots(data):
        lot_storage.clear()
        lot_storage.extend(data)

    def test_load_reservations():
        return [{
            "id": "res-1",
            "user_id": "1",
            "vehicle_id": str(uuid4()),
            "start_time": "2026-12-12T10:00",
            "end_time": "2026-12-12T12:00",
            "parking_lot_id": lot_id,
            "status": "pending"
        }]
    
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
    
    lot_storage.append({
        "id": lot_id,
        **ParkingLot(
            name="TEST",
            location="TEST_LOCATION",
            address="TEST_ADDRESS",
            capacity=10,
            reserved=0,
            tariff=2.50,
            daytariff=20.00,
            created_at="2025-12-12",
            coordinates=Coordinates(
                lat=40.712776,
                lng=-74.005974
            )
        ).model_dump()
    })

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
        "services.parking_services.storage_utils.save_parking_lot_data",
        test_save_lots
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
    assert len(session_storage) > 0
    assert session_storage[0]["licenseplate"] == "TEST-PLATE"
    assert lot_storage[0]["reserved"] == 1

def test_stop_parking_session(monkeypatch):
    session_user = {
        "username": "testuser",
        "role": "USER"
    }
    license_plate = "TEST-PLATE"
    lot_id = "999999"
    session_id = "999999"
    lot_storage = []
    session_storage = []

    def test_load_lots():
        return lot_storage.copy()

    def test_load_sessions():
        return session_storage.copy()
    
    def test_save_sessions(data):
        session_storage.clear()
        session_storage.extend(data)
    
    def test_save_lots(data):
        lot_storage.clear()
        lot_storage.extend(data)
    
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
        "services.parking_services.storage_utils.save_parking_session_data",
        test_save_sessions
    )
    
    monkeypatch.setattr(
        "services.parking_services.storage_utils.save_parking_lot_data",
        test_save_lots
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

    lot_storage.append({
        "id": lot_id,
        **ParkingLot(
            name="TEST",
            location="TEST_LOCATION",
            address="TEST_ADDRESS",
            capacity=10,
            reserved=1,
            tariff=2.50,
            daytariff=20.00,
            created_at="2025-12-12",
            coordinates=Coordinates(
                lat=40.712776,
                lng=-74.005974
            )
        ).model_dump()
    })

    session_storage.append({
        "id": session_id,
        "licenseplate": license_plate,
        "started": "2026-12-12T10:00:00",
        "stopped": None,
        "user": "testuser",
        "parking_lot_id": lot_id
    })

    session_data = ParkingSessionCreate(
        licenseplate = license_plate
    )

    result = parking_services.stop_parking_session(lot_id, session_data, session_user)
    
    assert result["licenseplate"] == license_plate
    assert result["stopped"] is not None
    assert "cost" in result
    assert result["payment_status"] == "Pending"
    assert "duration_minutes" in result

def test_update_parking_session(monkeypatch):
    lot_storage = []
    session_storage = []
    lot_id = "999999"
    session_id = "999999"
    license_plate = "TEST-PLATE-UPDATED"

    def test_load_lots():
        return lot_storage.copy()
    
    def test_load_sessions():
        return session_storage.copy()
    
    def test_save_sessions(data):
        session_storage.clear()
        session_storage.extend(data)
    
    lot_storage.append({
        "id": lot_id,
        **ParkingLot(
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
        ).model_dump()
    })
    
    session_storage.append({
        "id": session_id,
        "licenseplate": "TEST-PLATE",
        "started": "2026-12-12T10:00",
        "stopped": None,
        "user": "testuser"
    })
    
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
    assert session_storage[0]["licenseplate"] == license_plate

def test_delete_parking_session(monkeypatch):
    session_storage = []
    session_id = "999999"
    lot_id = "999999"

    def test_load_sessions():
        return session_storage.copy()
    
    def test_save_sessions(data):
        session_storage.clear()
        session_storage.extend(data)

    session_storage.append({
        "id": session_id,
        "licenseplate": "TEST-PLATE",
        "started": "2026-12-12T10:00",
        "stopped": None,
        "user": "testuser"
    })

    monkeypatch.setattr(
        "services.parking_services.storage_utils.load_parking_session_data",
        test_load_sessions
    )

    monkeypatch.setattr(
        "services.parking_services.storage_utils.save_parking_session_data",
        test_save_sessions
    )

    parking_services.delete_parking_session(session_id, lot_id)
    assert not any(session.get("id") == session_id for session in session_storage)