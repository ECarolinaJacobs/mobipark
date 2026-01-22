import requests
import json
import random
import string
import uuid
import sys
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def print_header(title):
    print(f"\n{'='*20} {title} {'='*20}")

def log_request(method, url, headers=None, body=None):
    print(f"[REQUEST] {method} {url}")
    if headers:
        headers_copy = headers.copy()
        if 'Authorization' in headers_copy:
            headers_copy['Authorization'] = headers_copy['Authorization'][:10] + "..."
        print(f"Headers: {json.dumps(headers_copy, indent=2)}")
    if body:
        print(f"Body: {json.dumps(body, indent=2)}")

def log_response(response):
    print(f"[RESPONSE] Status: {response.status_code}")
    try:
        if response.text:
            print(f"Body: {json.dumps(response.json(), indent=2)}")
        else:
            print("Body: (empty)")
    except Exception:
        print(f"Body: {response.text}")

def run_demo():
    print("Starting API Demo...")
    
    # Generate unique user
    rnd = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    username = f"user_{rnd}"
    password = "Password123!"
    
    # 1. Register
    print_header("1. Register New User")
    register_payload = {
        "username": username,
        "name": f"Demo User {rnd}",
        "password": password,
        "role": "USER",
        "email": f"{username}@example.com",
        "birth_year": 1995
    }
    
    resp = requests.post(f"{BASE_URL}/auth/register", json=register_payload)
    log_request("POST", "/auth/register", body=register_payload)
    log_response(resp)
    
    if resp.status_code != 200:
        print("Registration failed. Aborting.")
        return

    # 2. Login
    print_header("2. Login")
    login_payload = {
        "username": username,
        "password": password
    }
    resp = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    log_request("POST", "/auth/login", body=login_payload)
    log_response(resp)
    
    if resp.status_code != 200:
        print("Login failed. Aborting.")
        return
        
    token = resp.headers.get("Authorization")
    if not token:
        # Try finding it in body if not in header (though code says header)
        data = resp.json()
        token = data.get("session_token")
        
    if not token:
        print("Could not retrieve token. Aborting.")
        return
        
    headers = {"Authorization": token}
    print(f"\n[INFO] Token obtained: {token}")

    # 3. Get Profile
    print_header("3. Get Profile")
    resp = requests.get(f"{BASE_URL}/profile", headers=headers)
    log_request("GET", "/profile", headers=headers)
    log_response(resp)

    # 4. Create Vehicle
    print_header("4. Create Vehicle")
    # Dutch plate format: XX-99-99
    c = ''.join(random.choices(string.ascii_uppercase, k=2))
    d1 = ''.join(random.choices(string.digits, k=2))
    d2 = ''.join(random.choices(string.digits, k=2))
    plate = f"{c}-{d1}-{d2}"
    
    vehicle_payload = {
        "user_id": username,
        "license_plate": plate,
        "make": "DemoMake",
        "model": "DemoModel",
        "color": "Blue",
        "year": 2023
    }
    resp = requests.post(f"{BASE_URL}/vehicles", json=vehicle_payload, headers=headers)
    log_request("POST", "/vehicles", headers=headers, body=vehicle_payload)
    log_response(resp)
    
    if resp.status_code != 200:
        print("Vehicle creation failed.")
        vehicle_id = str(uuid.uuid4()) # fallback
    else:
        vehicle_id = resp.json().get("id")

    # 5. List Parking Lots
    print_header("5. List Parking Lots")
    resp = requests.get(f"{BASE_URL}/parking-lots/")
    log_request("GET", "/parking-lots/")
    log_response(resp)
    
    lots = resp.json()
    if lots:
        parking_lot_id = lots[0].get("id")
        print(f"Selected Parking Lot ID: {parking_lot_id}")
    else:
        print("No parking lots available. Skipping session/reservation steps.")
        return

    # 6. Start Session
    print_header("6. Start Parking Session")
    session_payload = {"licenseplate": plate}
    resp = requests.post(f"{BASE_URL}/parking-lots/{parking_lot_id}/sessions/start", json=session_payload, headers=headers)
    log_request("POST", f"/parking-lots/{parking_lot_id}/sessions/start", headers=headers, body=session_payload)
    log_response(resp)

    # Sleep briefly
    time.sleep(1)

    # 7. Stop Session
    print_header("7. Stop Parking Session")
    resp = requests.put(f"{BASE_URL}/parking-lots/{parking_lot_id}/sessions/stop", json=session_payload, headers=headers)
    log_request("PUT", f"/parking-lots/{parking_lot_id}/sessions/stop", headers=headers, body=session_payload)
    log_response(resp)
    
    # 8. Create Reservation
    print_header("8. Create Reservation")
    # Start tomorrow
    start_dt = datetime.now() + timedelta(days=1)
    end_dt = start_dt + timedelta(hours=2)
    start_str = start_dt.strftime("%Y-%m-%dT%H:%M")
    end_str = end_dt.strftime("%Y-%m-%dT%H:%M")
    
    reservation_payload = {
        "user_id": username,
        "vehicle_id": vehicle_id,
        "parking_lot_id": str(parking_lot_id),
        "start_time": start_str,
        "end_time": end_str
    }
    resp = requests.post(f"{BASE_URL}/reservations/", json=reservation_payload, headers=headers)
    log_request("POST", "/reservations/", headers=headers, body=reservation_payload)
    log_response(resp)
    
    # 9. Get Billing
    print_header("9. Get Billing")
    resp = requests.get(f"{BASE_URL}/billing", headers=headers)
    log_request("GET", "/billing", headers=headers)
    log_response(resp)

    # 10. Create Payment
    print_header("10. Create Payment")
    payment_payload = {
        "amount": 5.0,
        "session_id": 99999, # Dummy ID
        "parking_lot_id": int(parking_lot_id),
        "t_data": {
            "amount": 5.0,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "method": "ideal",
            "issuer": "ING",
            "bank": "ING"
        }
    }
    resp = requests.post(f"{BASE_URL}/payments", json=payment_payload, headers=headers)
    log_request("POST", "/payments", headers=headers, body=payment_payload)
    log_response(resp)

    print("\nDemo Completed Successfully!")

if __name__ == "__main__":
    run_demo()
