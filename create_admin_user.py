import json
import uuid
import sys
import os
from datetime import datetime

# Add project root to sys.path to import utils
sys.path.append(os.getcwd())

from utils.passwords import hash_password_bcrypt

USERS_FILE = "mock_data/mock_users.json"

def create_admin():
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    except FileNotFoundError:
        users = []

    # Check if demo_admin exists
    for user in users:
        if user.get("username") == "demo_admin":
            print("User 'demo_admin' already exists.")
            return

    print("Creating 'demo_admin'...")
    new_admin = {
        "id": str(uuid.uuid4()),
        "username": "demo_admin",
        "password": hash_password_bcrypt("admin123"),
        "name": "Demo Admin",
        "email": "admin@demo.com",
        "phone": "1234567890",
        "role": "ADMIN",
        "created_at": str(datetime.now()),
        "birth_year": 1980,
        "active": True,
        "managed_parking_lot_id": None,
        "hash_type": "bcrypt"
    }
    
    users.append(new_admin)
    
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)
    
    print("User 'demo_admin' created successfully.")

if __name__ == "__main__":
    create_admin()
