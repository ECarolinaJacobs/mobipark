import requests
import json
import random
import string
import uuid
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
ADMIN_USER = "demo_admin"
ADMIN_PASS = "admin123"

def print_header(title):
    print(f"\n{'='*20} {title} {'='*20}")

def log_request(method, url, headers=None, body=None):
    print(f"[REQUEST] {method} {url}")
    # if headers:
    #     headers_copy = headers.copy()
    #     if 'Authorization' in headers_copy:
    #         headers_copy['Authorization'] = headers_copy['Authorization'][:10] + "..."
    #     print(f"Headers: {json.dumps(headers_copy, indent=2)}")
    if body:
        print(f"Body: {json.dumps(body, indent=2)}")

def log_response(response):
    print(f"[RESPONSE] Status: {response.status_code}")
    try:
        print(f"Body: {json.dumps(response.json(), indent=2)}")
    except Exception:
        print(f"Body: {response.text}")

def get_headers(token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = token
    return h

def run_full_demo():
    print("Starting COMPREHENSIVE API Demo...")
    
    # ================= PHASE 1: ADMIN SETUP =================
    print_header("PHASE 1: ADMIN SETUP")
    
    # 1. Login Admin
    print("\n[1.1] Login Admin")
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    log_response(resp)
    if resp.status_code != 200:
        print("Admin login failed. Run 'create_admin_user.py' first.")
        return
    admin_token = resp.headers.get("Authorization") or resp.json().get("session_token")
    admin_headers = get_headers(admin_token)

    # 2. Create New Parking Lot
    print("\n[1.2] Admin Creates 'Downtown Plaza' Parking Lot")
    lot_id = str(random.randint(1000, 9999))
    lot_payload = {
        "id": lot_id, # Wait, model doesn't have ID in create?
        # Checking model: ParkingLot(BaseModel) fields: name, location...
        # endpoints/parking_lots.py: create_parking_lot(parking_lot: ParkingLot)
        # It calls parking_services.create_parking_lot. 
        # Usually ID is auto-generated or passed. Let's look at the Model again?
        # ParkingLot model in models/parking_lots_model.py doesn't have 'id' field?
        # Actually it might be generated.
        # But wait, create_parking_lot in service usually adds ID.
        # Let's check 'models/parking_lots_model.py' content from history... 
        # It has name, location, address, capacity... NO ID field in the class definition I saw.
        # But 'parking_services.create_parking_lot' implementation matters.
        # I'll Assume I don't send ID, and it returns one.
        "name": "Downtown Plaza",
        "location": "Center",
        "address": "Main St 1",
        "capacity": 50,
        "reserved": 0,
        "tariff": 4.5,
        "daytariff": 40.0,
        "created_at": datetime.now().isoformat(),
        "coordinates": {"lat": 52.0, "lng": 4.0}
    }
    # If the model expects these fields, I must provide them.
    # The 'ParkingLot' model in 'models/parking_lots_model.py' shown earlier:
    # class ParkingLot(BaseModel): name, location... (No ID)
    
    resp = requests.post(f"{BASE_URL}/parking-lots/", json=lot_payload, headers=admin_headers)
    log_response(resp)
    if resp.status_code == 200:
        created_lot = resp.json()
        new_lot_id = created_lot.get("id")
        print(f"Created Lot ID: {new_lot_id}")
    else:
        print("Failed to create lot. Using ID 1.")
        new_lot_id = "1"

    # 3. Create Global Discount Code
    print("\n[1.3] Admin Creates Global Discount Code 'SUMMER2026'")
    discount_payload = {
        "code": f"SUMMER{random.randint(100,999)}",
        "discount_type": "percentage",
        "discount_value": 20,
        "max_uses": 100,
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat()
    }
    resp = requests.post(f"{BASE_URL}/discount-codes", json=discount_payload, headers=admin_headers)
    log_response(resp)
    global_discount_code = discount_payload["code"]

    # 4. Register Hotel Manager
    print("\n[1.4] Admin Registers Hotel Manager for the new Lot")
    hotel_mgr_user = f"hotel_mgr_{random.randint(100,999)}"
    hotel_mgr_pass = "hotel123"
    hm_payload = {
        "username": hotel_mgr_user,
        "name": "Hotel Manager Bob",
        "password": hotel_mgr_pass,
        "parking_lot_id": new_lot_id,
        "email": "bob@hotel.com"
    }
    resp = requests.post(f"{BASE_URL}/auth/register/hotel-manager", json=hm_payload, headers=admin_headers)
    log_response(resp)


    # ================= PHASE 2: HOTEL MANAGER =================
    print_header("PHASE 2: HOTEL MANAGER ACTIONS")

    # 1. Login Hotel Manager
    print("\n[2.1] Login Hotel Manager")
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": hotel_mgr_user, "password": hotel_mgr_pass})
    log_response(resp)
    hm_token = resp.headers.get("Authorization") or resp.json().get("session_token")
    hm_headers = get_headers(hm_token)

    # 2. Get Managed Lot
    print("\n[2.2] Get Managed Parking Lot Details")
    resp = requests.get(f"{BASE_URL}/hotel-manager/managed-parking-lot", headers=hm_headers)
    log_response(resp)

    # 3. Create Hotel Discount Code
    print("\n[2.3] Create Hotel Guest Discount Code")
    hotel_code_val = f"HOTEL{random.randint(100,999)}"
    hotel_code_payload = {
        "code": hotel_code_val,
        "check_in_date": datetime.now().strftime("%Y-%m-%d"),
        "check_out_date": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "guest_name": "Alice Guest",
        "notes": "VIP Guest"
    }
    resp = requests.post(f"{BASE_URL}/hotel-manager/discount-codes", json=hotel_code_payload, headers=hm_headers)
    log_response(resp)


    # ================= PHASE 3: REGULAR USER JOURNEY =================
    print_header("PHASE 3: REGULAR USER JOURNEY")

    # 1. Register User
    print("\n[3.1] Register New User")
    user_rnd = ''.join(random.choices(string.ascii_lowercase, k=4))
    username = f"user_{user_rnd}"
    password = "UserPass123!"
    reg_payload = {
        "username": username,
        "name": f"Regular User {user_rnd}",
        "password": password,
        "role": "USER",
        "birth_year": 1995
    }
    resp = requests.post(f"{BASE_URL}/auth/register", json=reg_payload)
    log_response(resp)

    # 2. Login
    print("\n[3.2] Login User")
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    user_token = resp.headers.get("Authorization") or resp.json().get("session_token")
    user_headers = get_headers(user_token)
    print(f"User Token: {user_token}")

    # 3. Update Profile
    print("\n[3.3] Update Profile (Add Phone)")
    resp = requests.put(f"{BASE_URL}/profile", json={"phone": "555-0199"}, headers=user_headers)
    log_response(resp)

    # 4. Create Vehicle
    print("\n[3.4] Register Vehicle")
    plate = f"AB-{random.randint(10,99)}-{random.randint(10,99)}"
    veh_payload = {
        "user_id": username,
        "license_plate": plate,
        "make": "Toyota",
        "model": "Camry",
        "color": "Silver",
        "year": 2022
    }
    resp = requests.post(f"{BASE_URL}/vehicles", json=veh_payload, headers=user_headers)
    log_response(resp)
    vehicle_id = resp.json().get("id")

    # 5. Start Parking Session
    print("\n[3.5] Start Parking Session")
    resp = requests.post(f"{BASE_URL}/parking-lots/{new_lot_id}/sessions/start", json={"licenseplate": plate}, headers=user_headers)
    log_response(resp)
    # The response should have session details.
    session_data = resp.json()
    # If the response has 'id', that's the session ID. 
    # NOTE: The create_parking_session usually returns the session object.
    
    # 6. Stop Session (Simulate time pass?)
    # We can't easily simulate time pass on server without waiting, so it will be 0 duration.
    time.sleep(1)
    print("\n[3.6] Stop Parking Session")
    resp = requests.put(f"{BASE_URL}/parking-lots/{new_lot_id}/sessions/stop", json={"licenseplate": plate}, headers=user_headers)
    log_response(resp)
    stop_data = resp.json()
    
    # We need the SESSION ID for payment.
    # The 'stop' response might contain 'id' or we need to find it from 'start'.
    # Looking at 'endpoints/parking_lots.py', 'stop_parking_session' returns the stopped session object.
    # The 'start' also returns it.
    session_id = session_data.get("id") or stop_data.get("id") 
    print(f"Session ID: {session_id}")

    # 7. Create Reservation (Future)
    print("\n[3.7] Create Future Reservation")
    start_t = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%dT10:00")
    end_t = (datetime.now() + timedelta(days=5, hours=4)).strftime("%Y-%m-%dT14:00")
    res_payload = {
        "vehicle_id": vehicle_id,
        "parking_lot_id": new_lot_id,
        "start_time": start_t,
        "end_time": end_t
    }
    resp = requests.post(f"{BASE_URL}/reservations/", json=res_payload, headers=user_headers)
    log_response(resp)

    # 8. Create Payment (with Discount)
    print("\n[3.8] Pay for Session with Global Discount")
    pay_amount = 10.0 # Arbitrary amount since duration was 0
    pay_payload = {
        "amount": pay_amount,
        "session_id": int(session_id) if session_id and session_id.isdigit() else 99999, # Handle if ID is UUID
        "parking_lot_id": int(new_lot_id) if new_lot_id and new_lot_id.isdigit() else 1,
        "discount_code": global_discount_code,
        "t_data": {
            "amount": pay_amount,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "method": "creditcard",
            "issuer": "MasterCard",
            "bank": "Citi"
        }
    }
    # Note: payment model expects session_id/parking_lot_id as int or str?
    # PaymentCreate model says: session_id: int, parking_lot_id: int.
    # But my lot ID might be string if I used random.
    # If the backend enforces int, I must ensure they are ints.
    # The 'create_payment' endpoint converts them to string for storage but expects int in input model?
    # endpoints/payments_endpoint.py: class PaymentCreate(BaseModel): session_id: int, parking_lot_id: int
    # So I must ensure they are integers.
    
    resp = requests.post(f"{BASE_URL}/payments", json=pay_payload, headers=user_headers)
    log_response(resp)
    payment_data = resp.json()
    transaction_id = payment_data.get("transaction")


    # ================= PHASE 4: ADMIN MANAGEMENT =================
    print_header("PHASE 4: ADMIN MANAGEMENT")

    # 1. View All Payments
    print("\n[4.1] Admin Views All Payments")
    resp = requests.get(f"{BASE_URL}/payments", headers=admin_headers)
    # log_response(resp) # Too verbose if many payments
    print(f"Status: {resp.status_code}")
    print(f"Count: {len(resp.json())}")

    # 2. Refund the User's Payment
    if transaction_id:
        print(f"\n[4.2] Admin Refunds Transaction {transaction_id}")
        refund_payload = {
            "original_transaction_id": transaction_id,
            "amount": 2.0, # Partial refund
            "reason": "Customer complaint resolved"
        }
        resp = requests.post(f"{BASE_URL}/refunds", json=refund_payload, headers=admin_headers)
        log_response(resp)
    
    # 3. View All Refunds
    print("\n[4.3] Admin Views All Refunds")
    resp = requests.get(f"{BASE_URL}/refunds", headers=admin_headers)
    print(f"Status: {resp.status_code}")
    print(f"Count: {len(resp.json())}")
    
    # 4. Deactivate Discount Code
    print("\n[4.4] Admin Deactivates Global Discount Code")
    resp = requests.delete(f"{BASE_URL}/discount-codes/{global_discount_code}", headers=admin_headers)
    log_response(resp)


    # ================= PHASE 5: CLEANUP =================
    print_header("PHASE 5: CLEANUP")

    # 1. Delete Vehicle
    print("\n[5.1] User Deletes Vehicle")
    resp = requests.delete(f"{BASE_URL}/vehicles/{plate}", headers=user_headers)
    log_response(resp)

    # 2. Delete Parking Lot (Admin)
    print(f"\n[5.2] Admin Deletes Parking Lot {new_lot_id}")
    resp = requests.delete(f"{BASE_URL}/parking-lots/{new_lot_id}", headers=admin_headers)
    log_response(resp)

    print("\nFULL DEMO COMPLETE.")

if __name__ == "__main__":
    run_full_demo()
