import csv
import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()
use_mock_data = os.getenv("USE_MOCK_DATA", "true") == "true"
MOCK_PARKING_LOTS = (Path(__file__).parent.parent / "mock_data/mock_parking-lots.json").resolve()
MOCK_PARKING_SESSIONS = (Path(__file__).parent.parent / "mock_data/pdata/mock_parkingsessions.json").resolve()
MOCK_USERS = (Path(__file__).parent.parent / "mock_data/mock_users.json").resolve()
MOCK_RESERVATIONS = (Path(__file__).parent.parent / "mock_data/mock_reservations.json").resolve()
MOCK_PAYMENTS = (Path(__file__).parent.parent / "mock_data/mock_payments.json").resolve()
MOCK_BILLING = (Path(__file__).parent.parent / "mock_data/mock_billing.json").resolve()
MOCK_DISCOUNTS = (Path(__file__).parent.parent / "mock_data/mock_discounts.json").resolve()
MOCK_REFUNDS = (Path(__file__).parent.parent / "mock_data/mock_refunds.json").resolve()
MOCK_VEHICLES = (Path(__file__).parent.parent / "mock_data/mock_vehicles.json").resolve()


# Define the database path globally
# Check for test database path first (for pytest)
if os.getenv("TEST_DB_PATH"):
    DB_PATH = Path(os.getenv("TEST_DB_PATH"))
else:
    DB_PATH = Path(__file__).parent / "../data/mobypark.db"


def init_db():
    """
    Initializes the database and creates tables if they don't exist.
    """
    # Create the data directory if it doesn't exist
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT,
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                name TEXT,
                email TEXT,
                phone_number TEXT,
                role TEXT,
                created_at TEXT,
                birth_year INTEGER,
                is_active INTEGER DEFAULT 1,
                last_login TEXT,
                hash_type TEXT
            )
        """)

        # Create parking_lots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parking_lots (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
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
        """)

        # create parking sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parking_sessions (
            id TEXT PRIMARY KEY,
            parking_lot_id text,
            licenseplate TEXT,
            started TEXT,
            stopped TEXT,
            user TEXT,
            duration_minutes INTEGER,
            cost REAL,
            payment_status TEXT,
            FOREIGN KEY (parking_lot_id) REFERENCES parking_lots (id)

            ) """)
                       
        # Create reservations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                vehicle_id TEXT,
                parking_lot_id TEXT,
                start_time TEXT,
                end_time TEXT,
                cost REAL,
                status TEXT,
                created_at TEXT
            )
        """)

        # Create payments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                "transaction" TEXT PRIMARY KEY,
                amount REAL,
                initiator TEXT,
                created_at TEXT,
                completed TEXT,
                hash TEXT,
                session_id TEXT,
                parking_lot_id TEXT,
                original_amount REAL,
                discount_applied TEXT,
                discount_amount REAL,
                "t_data.amount" REAL,
                "t_data.date" TEXT,
                "t_data.method" TEXT,
                "t_data.issuer" TEXT,
                "t_data.bank" TEXT
            )
        """)

        # Create discounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discounts (
                code TEXT PRIMARY KEY,
                discount_type TEXT,
                discount_value REAL,
                max_uses INTEGER,
                current_uses INTEGER,
                active INTEGER,
                created_at TEXT,
                expires_at TEXT
            )
        """)

        # Create refunds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refunds (
                refund_id TEXT PRIMARY KEY,
                original_transaction_id TEXT,
                amount REAL,
                reason TEXT,
                status TEXT,
                created_at TEXT,
                processed_by TEXT,
                refund_hash TEXT
            )
        """)

        # Create vehicles table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            license_plate TEXT NOT NULL,
            make TEXT,
            model TEXT,
            color TEXT,
            year INTEGER,
            is_default INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (username)
        )
    """)

        conn.commit()
        print("Database Created")


# Call the init function at the start of the script
init_db()


# --- General Normalization/Unnormalization Functions (RETAINED) ---


def normalize_data(data: List[Dict]) -> List[Dict]:
    """
    Recursively normalizes all nested dictionaries into a flat structure
    using dot notation (e.g., {'coords': {'lan': 9}} -> {'coords.lan': 9}).
    Applies to a list of dictionaries.
    """
    normalized_list = []

    def flatten_dict(d: Dict) -> Dict:
        """Helper function to flatten a single dictionary."""
        flat_dict = {}
        for k, v in d.items():
            if isinstance(v, dict):
                # Recursively flatten nested dictionary
                nested_flat = flatten_dict(v)
                for nested_k, nested_v in nested_flat.items():
                    flat_dict[f"{k}.{nested_k}"] = nested_v
            else:
                flat_dict[k] = v
        return flat_dict

    for item in data:
        normalized_list.append(flatten_dict(item))

    return normalized_list


def unnormalize_data(data: List[Dict]) -> List[Dict]:
    """
    Unnormalizes dot-separated keys back into a nested dictionary structure
    (e.g., {'coords.lan': 9} -> {'coords': {'lan': 9}}).
    Applies to a list of dictionaries.
    """
    unnormalized_list = []

    def unflatten_dict(d: Dict) -> Dict:
        """Helper function to unflatten a single dictionary."""
        final_unflat_dict = {}
        temp_nested_parts = {}

        # 1. Process all keys
        for k, v in d.items():
            if "." not in k:
                # Copy non-dot-separated keys (base columns)
                final_unflat_dict[k] = v
            else:
                # 2. Reconstruct the nested structure from dot-separated keys
                parts = k.split(".")
                current_dict = temp_nested_parts
                for part in parts[:-1]:
                    if part not in current_dict:
                        current_dict[part] = {}
                    current_dict = current_dict[part]
                current_dict[parts[-1]] = v

        # 3. Merge the reconstructed nested parts into the final dictionary
        for k, v in temp_nested_parts.items():
            # If the key already exists (from a base column) and is a dictionary, merge; otherwise overwrite.
            if (
                k in final_unflat_dict
                and isinstance(final_unflat_dict[k], dict)
                and isinstance(v, dict)
            ):
                final_unflat_dict[k].update(v)
            else:
                final_unflat_dict[k] = v

        return final_unflat_dict

    for item in data:
        unnormalized_list.append(unflatten_dict(item))

    return unnormalized_list


# --- Utility Function to Get Column Names (RETAINED) ---


def get_table_columns(table_name: str) -> List[str]:
    """
    Retrieves the column names from a specified SQLite table using a temporary connection.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name!r})")
            columns = [info[1] for info in cursor.fetchall()]
            return columns
    except sqlite3.OperationalError as e:
        print(f"Error retrieving columns for table '{table_name}': {e}")
        return []


# --- Database I/O Functions (OPTIMIZED FOR TARGETED QUERIES) ---


def load_json_from_db(table_name: str) -> List[Dict]:
    """
    Loads ALL data from a table (used for the /payments endpoint).
    """
    normalized_data = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name!r}")
            for row in cursor:
                normalized_data.append(dict(row))
    except sqlite3.OperationalError as e:
        print(f"Error loading all data from table '{table_name}': {e}")
        return []

    return unnormalize_data(normalized_data)


def load_single_json_from_db(
    table_name: str, key_col: str, key_val: str
) -> Optional[Dict]:
    """
    Loads a single row using a WHERE clause.
    """
    normalized_data = None
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            sql = f'SELECT * FROM "{table_name}" WHERE "{key_col}" = ?'
            cursor.execute(sql, (key_val,))

            row = cursor.fetchone()
            if row:
                normalized_data = dict(row)

    except sqlite3.OperationalError as e:
        print(f"Error loading single data from table '{table_name}': {e}")
        return None

    if normalized_data:
        # unnormalize_data expects a list, so wrap/unwrap the result
        return unnormalize_data([normalized_data])[0]
    return None


def insert_single_json_to_db(table_name: str, item: Dict):
    """
    Inserts a single dictionary/row into the table.
    """
    # 1. Normalize the data (single item)
    normalized_data = normalize_data([item])[0]

    # 2. Determine columns and values
    insert_columns = list(normalized_data.keys())
    values_to_insert = tuple(normalized_data.values())

    # 3. Construct SQL statement
    column_names_sql = ", ".join([f'"{col}"' for col in insert_columns])
    placeholders_sql = ", ".join(["?"] * len(insert_columns))
    sql_insert = (
        f"INSERT INTO {table_name} ({column_names_sql}) VALUES ({placeholders_sql})"
    )

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(sql_insert, values_to_insert)
            conn.commit()
    except sqlite3.OperationalError as e:
        print(f"Error inserting data to table '{table_name}': {e}")
        raise


def update_single_json_in_db(
    table_name: str, key_col: str, key_val: str, update_item: Dict
):
    """
    Updates a single existing row in the table based on a key column.
    The update_item must contain the complete, final state of the object.
    """
    # 1. Normalize the complete, final data (single item)
    normalized_data = normalize_data([update_item])[0]

    # 2. Determine columns and values for the SET clause
    set_clauses = []
    values_to_update = []
    for col, val in normalized_data.items():
        set_clauses.append(f'"{col}" = ?')
        values_to_update.append(val)

    values_to_update.append(key_val)  # Add the WHERE clause value last

    # 3. Construct SQL statement
    set_sql = ", ".join(set_clauses)
    sql_update = f'UPDATE "{table_name}" SET {set_sql} WHERE "{key_col}" = ?'

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(sql_update, tuple(values_to_update))

            if cursor.rowcount == 0:
                # Note: This raises an error if no row was found to update, which helps the endpoint return a 404/error.
                raise ValueError(f"No row found with {key_col}={key_val} to update.")

            conn.commit()
    except (sqlite3.OperationalError, ValueError) as e:
        print(f"Error updating data in table '{table_name}': {e}")
        raise


def save_json_to_db(table_name, data):
    """
    Saves a list of dictionaries by normalizing the data and using
    executemany for bulk, efficient insertion (Used only for full dump/refresh scenarios).
    The single item insert/update functions are preferred for endpoint operations.
    """

    # 1. Normalize the data
    normalized_data = normalize_data(data)

    # If no data, just delete and exit
    if not normalized_data:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(f"DELETE FROM {table_name}")
                conn.commit()
            return
        except sqlite3.OperationalError as e:
            print(f"Error deleting data from table '{table_name}': {e}")
            return

    # 2. Determine columns for insertion
    insert_columns = list(normalized_data[0].keys())

    # 3. Prepare data for bulk insert
    values_to_insert = []
    for item in normalized_data:
        values_to_insert.append(tuple(item.get(col, None) for col in insert_columns))

    # 4. Construct SQL statement
    column_names_sql = ", ".join([f'"{col}"' for col in insert_columns])
    placeholders_sql = ", ".join(["?"] * len(insert_columns))

    sql_insert = (
        f"INSERT INTO {table_name} ({column_names_sql}) VALUES ({placeholders_sql})"
    )
    sql_delete = f"DELETE FROM {table_name}"

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(sql_delete)
            cursor.executemany(sql_insert, values_to_insert)
    except sqlite3.OperationalError as e:
        print(f"Error saving data to table '{table_name}': {e}")


# -----------------------------------------------------------------
## 🗄️ Specific Application Database I/O Functions (MIGRATED TO TARGETED)
# -----------------------------------------------------------------


# --- Users ---
def load_user_data_from_db():
    if use_mock_data:
        return load_data(MOCK_USERS)
    return load_json_from_db("users")


def save_user_data_to_db(data):
    if use_mock_data:
        users = load_data(MOCK_USERS)
        users.append(data)
        save_data(MOCK_USERS, users)
        return
    save_json_to_db("users", data)


# Targeted access (example for other entities)
def get_user_data_by_username(username: str) -> Optional[Dict]:
    if use_mock_data:
        users = load_data(MOCK_USERS)
        for user in users:
            if user.get("username") == username:
                return user
        return None
    return load_single_json_from_db("users", key_col="username", key_val=username)

def update_existing_user_in_db(username: str, user_data: Dict):
    if use_mock_data:
        users = load_data(MOCK_USERS)
        for user in users:
            if user.get("username") == username:
                user.update(user_data)
                save_data(MOCK_USERS, users)
                return
        raise ValueError("User not found")
    
    update_single_json_in_db(
        "users", 
        key_col="username", 
        key_val=username, 
        update_item=user_data
    )

# --- Parking Lots ---
def load_parking_lot_data_from_db():
    if use_mock_data:
        return load_data(MOCK_PARKING_LOTS)
    return load_json_from_db("parking_lots")


def save_parking_lot_data_to_db(data):
    if use_mock_data:
        parking_lots = load_data(MOCK_PARKING_LOTS)
        lot_id = data.get("id")
        parking_lots[lot_id] = data
        save_data(MOCK_PARKING_LOTS, parking_lots)
        return
    save_json_to_db("parking_lots", data)


# --- Reservations ---
def load_reservation_data_from_db():
    if use_mock_data:
        return load_data(MOCK_RESERVATIONS)
    return load_json_from_db("reservations")


def save_reservation_data_to_db(data):
    if use_mock_data:
        reservations = load_data(MOCK_RESERVATIONS)
        reservations.append(data)
        save_data(MOCK_RESERVATIONS, reservations)
        return
    save_json_to_db("reservations", data)


# --- Payments (Targeted functions for /payments endpoint) ---
def load_payment_data_from_db():
    if use_mock_data:
        return load_data(MOCK_PAYMENTS)
    return load_json_from_db("payments")


def get_payment_data_by_id(payment_id: str) -> Optional[Dict]:
    if use_mock_data:
        payments = load_data(MOCK_PAYMENTS)
        for payment in payments:
            if payment.get("transaction") == payment_id:
                return payment
        return None
    return load_single_json_from_db(
        "payments", key_col="transaction", key_val=payment_id
    )


def get_payments_by_initiator(initiator: str) -> List[Dict]:
    """
    Loads payments for a specific user using a WHERE clause.
    """
    if use_mock_data:
        payments = load_data(MOCK_PAYMENTS)
        return [p for p in payments if p.get("initiator") == initiator]

    normalized_data = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM payments WHERE "initiator" = ?', (initiator,))
            for row in cursor:
                normalized_data.append(dict(row))
    except sqlite3.OperationalError as e:
        print(f"Error loading payments for initiator '{initiator}': {e}")
        return []

    return unnormalize_data(normalized_data)


def get_refunds_for_user(username: str) -> List[Dict]:
    """
    Retrieves all refunds associated with payments made by a specific user.
    Uses a JOIN to avoid N+1 queries.
    """
    if use_mock_data:
        # Mock data implementation (inefficient but consistent with mock behavior)
        user_payments = [p for p in load_data(MOCK_PAYMENTS) if p.get("initiator") == username]
        transaction_ids = {p.get("transaction") for p in user_payments}
        all_refunds = load_data(MOCK_REFUNDS)
        return [r for r in all_refunds if r.get("original_transaction_id") in transaction_ids]

    normalized_data = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Select all columns from refunds table
            sql = """
                SELECT r.* 
                FROM refunds r
                JOIN payments p ON r.original_transaction_id = p."transaction"
                WHERE p.initiator = ?
            """
            cursor.execute(sql, (username,))
            for row in cursor:
                normalized_data.append(dict(row))
    except sqlite3.OperationalError as e:
        print(f"Error loading refunds for user '{username}': {e}")
        return []

    return unnormalize_data(normalized_data)


def save_new_payment_to_db(payment_data: Dict):
    if use_mock_data:
        payments = load_data(MOCK_PAYMENTS)
        payments.append(payment_data)
        save_data(MOCK_PAYMENTS, payments)
        return
    insert_single_json_to_db("payments", payment_data)


def update_existing_payment_in_db(payment_id: str, payment_data: Dict):
    if use_mock_data:
        payments = load_data(MOCK_PAYMENTS)
        for payment in payments:
            if payment.get("transaction") == payment_id:
                payment.update(payment_data)
                save_data(MOCK_PAYMENTS, payments)
                return
        raise ValueError("Payment not found")
    update_single_json_in_db(
        "payments", key_col="transaction", key_val=payment_id, update_item=payment_data
    )


# DEPRECATED/REMOVED: save_payment_data_to_db (Use save_new_payment_to_db or update_existing_payment_in_db)
# The original save_payment_data_to_db is effectively replaced by the full save_json_to_db('payments', data) if a full rewrite is needed.
# For API calls, the targeted functions above are used.


# --- Discounts ---
def load_discounts_data_from_db():
    if use_mock_data:
        return load_data(MOCK_DISCOUNTS)
    return load_json_from_db("discounts")


def get_discount_by_code(discount_code: str) -> Optional[Dict]:
    if use_mock_data:
        discounts = load_data(MOCK_DISCOUNTS)
        for discount in discounts:
            if discount.get("code") == discount_code:
                return discount
        return None
    return load_single_json_from_db("discounts", key_col="code", key_val=discount_code)


def save_new_discount_to_db(discount_data: Dict):
    if use_mock_data:
        discounts = load_data(MOCK_DISCOUNTS)
        discounts.append(discount_data)
        save_data(MOCK_DISCOUNTS, discounts)
        return
    insert_single_json_to_db("discounts", discount_data)


def update_existing_discount_in_db(discount_code: str, discount_data: Dict):
    if use_mock_data:
        discounts = load_data(MOCK_DISCOUNTS)
        for discount in discounts:
            if discount.get("code") == discount_code:
                discount.update(discount_data)
                save_data(MOCK_DISCOUNTS, discounts)
                return
        raise ValueError("Discount not found")
    update_single_json_in_db(
        "discounts", key_col="code", key_val=discount_code, update_item=discount_data
    )


def save_discounts_data_to_db(data):
    if use_mock_data:
        discounts = load_data(MOCK_DISCOUNTS)
        discounts.append(data)
        save_data(MOCK_DISCOUNTS, discounts)
        return
    save_json_to_db("discounts", data)


# --- Refunds ---
def load_refunds_data_from_db():
    if use_mock_data:
        return load_data(MOCK_REFUNDS)
    return load_json_from_db("refunds")


def get_refund_by_id(refund_id: str) -> Optional[Dict]:
    if use_mock_data:
        refunds = load_data(MOCK_REFUNDS)
        for refund in refunds:
            if refund.get("refund_id") == refund_id:
                return refund
        return None
    return load_single_json_from_db("refunds", key_col="refund_id", key_val=refund_id)


def save_new_refund_to_db(refund_data: Dict):
    if use_mock_data:
        refunds = load_data(MOCK_REFUNDS)
        refunds.append(refund_data)
        save_data(MOCK_REFUNDS, refunds)
        return
    insert_single_json_to_db("refunds", refund_data)


def update_existing_refund_in_db(refund_id: str, refund_data: Dict):
    if use_mock_data:
        refunds = load_data(MOCK_REFUNDS)
        for refund in refunds:
            if refund.get("refund_id") == refund_id:
                refund.update(refund_data)
                save_data(MOCK_REFUNDS, refunds)
                return
        raise ValueError("Refund not found")
    update_single_json_in_db(
        "refunds", key_col="refund_id", key_val=refund_id, update_item=refund_data
    )


def get_refunds_by_transaction_id(transaction_id: str) -> List[Dict]:
    """Get all refunds for a specific transaction"""
    if use_mock_data:
        filtered_refunds = []
        refunds = load_data(MOCK_REFUNDS)
        for refund in refunds:
            if refund.get("original_transaction_id") == transaction_id:
                filtered_refunds.append(refund)
        return filtered_refunds
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM refunds WHERE "original_transaction_id" = ?',
                (transaction_id,),
            )
            rows = cursor.fetchall()
            normalized_data = [dict(row) for row in rows]
            return unnormalize_data(normalized_data)
    except Exception as e:
        print(f"Error loading refunds for transaction {transaction_id}: {e}")
        return []


# -----------------------------------------------------------------
# 📄 File I/O Functions (Original - Retained for other file formats)
# -----------------------------------------------------------------


def load_json(filename):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def write_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, default=str)


def load_csv(filename):
    try:
        with open(filename, "r") as file:
            reader = csv.reader(file)
            return [row for row in reader]
    except FileNotFoundError:
        return []


def write_csv(filename, data):
    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        for row in data:
            writer.writerow(row)


def load_text(filename):
    try:
        with open(filename, "r") as file:
            return file.readlines()
    except FileNotFoundError:
        return []


def write_text(filename, data):
    with open(filename, "w") as file:
        for line in data:
            file.write(line + "\n")


# --- General File Save/Load Functions (Existing) ---


def save_data(filename, data):
    if str(filename).endswith(".json"):
        write_json(filename, data)
    elif filename.endswith(".csv"):
        write_csv(filename, data)
    elif filename.endswith(".txt"):
        write_text(filename, data)
    else:
        raise ValueError("Unsupported file format")


def load_data(filename):
    if str(filename).endswith(".json"):
        return load_json(filename)
    elif filename.endswith(".csv"):
        return load_csv(filename)
    elif filename.endswith(".txt"):
        return load_text(filename)
    else:
        return None


# --- Specific Application File I/O Functions (Updated to use DB when applicable) ---


def load_user_data():
    if use_mock_data:
        return load_data(MOCK_USERS)
    return load_user_data_from_db()


def save_user_data(data):
    if use_mock_data:
        save_data(MOCK_USERS, data)
        return
    return save_user_data_to_db(data)


def load_parking_lot_data():
    if use_mock_data:
        return load_data(MOCK_PARKING_LOTS)
    return load_parking_lot_data_from_db()


def save_parking_lot_data(data):
    if use_mock_data:
        save_data(MOCK_PARKING_LOTS, data)
        return
    return save_parking_lot_data_to_db(data)


# def find_parking_session_id_by_plate(parking_lot_id: str, licenseplate="TEST-PLATE"):
#     filename = f"./data/pdata/p{parking_lot_id}-sessions.json"
#     if use_mock_data:
#         filename = MOCK_PARKING_SESSIONS
#     with open(filename, "r") as f:
#         parking_lots = json.load(f)

#     for k, v in parking_lots.items():
#         if v.get("licenseplate") == licenseplate:
#             return k
    #verander dit naar db , wordt gebruikt in parkingservice bij stop parking session


def load_reservation_data():
    if use_mock_data:
        return load_data(MOCK_RESERVATIONS)
    return load_reservation_data_from_db()


def save_reservation_data(data):
    if use_mock_data:
        save_data(MOCK_RESERVATIONS, data)
        return
    return save_reservation_data_to_db(data)


def load_payment_data():
    if use_mock_data:
        return load_data(MOCK_PAYMENTS)
    return load_payment_data_from_db()


def save_payment_data(data):
    if use_mock_data:
        save_data(MOCK_PAYMENTS, data)
        return
    save_json_to_db("payments", data)


def load_discounts_data():
    if use_mock_data:
        return load_data(MOCK_DISCOUNTS)
    return load_discounts_data_from_db()


def save_discounts_data(data):
    if use_mock_data:
        save_data(MOCK_DISCOUNTS, data)
        return
    return save_discounts_data_to_db(data)


def load_refunds_data():
    if use_mock_data:
        return load_data(MOCK_REFUNDS)
    return load_refunds_data_from_db()


def save_refunds_data(data):
    # Refunds uses individual save/update mostly, but for bulk save:
    if use_mock_data:
        save_data(MOCK_REFUNDS, data)
        return
    save_json_to_db("refunds", data)

# def save_parking_session_data(data, lid):
#     if use_mock_data:
#         save_data(MOCK_PARKING_SESSIONS, data)
#         return
#     save_data(f"data/pdata/p{lid}-sessions.json", data)
# is vervangt door save_parking_session_data_to_db beneden

# def load_parking_session_data(lid):
#     if use_mock_data:
#          return load_data(MOCK_PARKING_SESSIONS)
#     return load_data(f"data/pdata/p{lid}-sessions.json")
# word niet eens gebruikt?


# vehicles
VEHICLE_FILE = "data/vehicles.json"


def load_vehicle_data():
    if use_mock_data:
        return load_data(MOCK_VEHICLES)
    return load_vehicle_data_from_db()


def save_vehicle_data(data):
    if use_mock_data:
        save_data(MOCK_VEHICLES, data)
        return
    return save_vehicle_data_to_db(data)


def get_vehicle_data_by_id(vehicle_id: str):
    """Return a single vehicle by its id (license or internal)."""
    vehicles = load_vehicle_data()
    for vehicle in vehicles:
        # allow lookup by 'id' or 'license_plate' key
        if (
            vehicle.get("id") == vehicle_id
            or vehicle.get("license_plate", "").replace("-", "").upper()
            == vehicle_id.upper()
        ):
            return vehicle
    return None


def get_vehicle_data_by_user(user_id: str):
    """Return all vehicles owned by a specific user."""
    vehicles = None
    if use_mock_data:
        vehicles = load_vehicle_data()
    else:
        vehicles = load_json_from_db("vehicles")
    return [v for v in vehicles if v.get("user_id") == user_id]


def save_new_vehicle_to_db(vehicle_data: Dict):
    """
    Append a new vehicle to vehicles.json.
    Maintains consistency with other *_data_to_db functions.
    """
    vehicles = load_vehicle_data()

    # Prevent duplicate license plates
    if any(
        v.get("license_plate", "").replace("-", "").upper()
        == vehicle_data.get("license_plate", "").replace("-", "").upper()
        for v in vehicles
    ):
        raise ValueError("Vehicle already exists")

    vehicles.append(vehicle_data)
    if use_mock_data:
        save_data(MOCK_VEHICLES, vehicles)
        return
    save_vehicle_data(vehicles)


def update_existing_vehicle_in_db(vehicle_id: str, vehicle_data: Dict):
    if use_mock_data:
        vehicles = load_vehicle_data()
        for vehicle in vehicles:
            if vehicle.get("id") == vehicle_id:
                vehicle.update(vehicle_data)
                save_data(MOCK_VEHICLES, vehicles)
                return
        raise ValueError("Vehicle not found")
    update_single_json_in_db("vehicles", "id", vehicle_id, vehicle_data)


def delete_vehicle_from_db(vehicle_id: str):
    if use_mock_data:
        vehicles = load_vehicle_data()
        new_vehicles = [vehicle for vehicle in vehicles if vehicle.get("id") != vehicle_id]
        if len(new_vehicles) == len(vehicles):
            raise ValueError("Vehicle not found")
        save_data(MOCK_VEHICLES, new_vehicles)
        return True

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vehicles WHERE id == ?", (vehicle_id,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.OperationalError as e:
        print(f"Error deleting vehicle: {e}")
        return False


def get_user_data_by_username_for_vehicles(username: str) -> Optional[Dict]:
    if use_mock_data:
        users = load_data(MOCK_USERS)
        for user in users:
            if user.get("username") == username:
                return user
        return None
    return load_single_json_from_db("users", "username", username)


def load_vehicle_data_from_db():
    if use_mock_data:
        return load_data(MOCK_VEHICLES)
    return load_json_from_db("vehicles")


def save_vehicle_data_to_db(data):
    if use_mock_data:
        vehicles = load_data(MOCK_VEHICLES)
        vehicles.append(data)
        return save_data(MOCK_VEHICLES, vehicles)
    insert_single_json_to_db("vehicles", data)


# --- parking sessions ---
def load_parking_sessions_data_from_db():
    if use_mock_data:
        return load_data(MOCK_PARKING_SESSIONS)
    return load_json_from_db("parking_sessions")

# Get all parking sessions for a specific parking lot ID
def get_sessions_data_by_id(parking_lot_id: str) -> Dict[str, Dict]:
    try:
        sessions = load_parking_sessions_data_from_db()
    except Exception:
        return {}

    filtered_sessions = [
        s for s in sessions
        if s.get("parking_lot_id") == str(parking_lot_id)
    ]

    return {s.get("id"): s for s in filtered_sessions}



def get_user_by_id(user_id) -> Optional[Dict]:
    if use_mock_data:
        users = load_data(MOCK_USERS)
        for user in users:
            if user.get("id") == user_id:
                return user
        return None
    return load_single_json_from_db("users", "id", user_id)


def save_parking_session_data(data):
    if use_mock_data:
        save_data(MOCK_PARKING_SESSIONS, data)
        return
    return save_parking_session_data_to_db(data)


def load_parking_session_data():
    if use_mock_data:
        return load_data(MOCK_PARKING_SESSIONS)
    return load_parking_sessions_data_from_db()


# def save_parking_session_data(data: Dict[str, Dict], parking_lot_id: str):
#     if use_mock_data:
#         try:
#             sessions = load_data(MOCK_PARKING_SESSIONS) or []
#         except Exception:
#             sessions = []

#         # Merge or replace by id into the centrale list
#         for sid, session in (data or {}).items():
#             session_obj = dict(session)
#             session_obj["id"] = sid
#             session_obj["parking_lot_id"] = str(parking_lot_id)

#             found = False
#             for i, s in enumerate(sessions):
#                 if s.get("id") == sid:
#                     sessions[i] = session_obj
#                     found = True
#                     break
#             if not found:
#                 sessions.append(session_obj)

#         save_data(MOCK_PARKING_SESSIONS, sessions)
#         return

#     for sid, session in (data or {}).items():
#         session_obj = dict(session)
#         session_obj["id"] = sid
#         session_obj["parking_lot_id"] = parking_lot_id
#         save_parking_session_data_to_db(session_obj)


def save_vehicle_data_to_db(data):
    if use_mock_data:
        vehicles = load_data(MOCK_VEHICLES)
        vehicles.append(data)
        return save_data(MOCK_VEHICLES, vehicles)
    insert_single_json_to_db("vehicles", data)


def save_parking_session_data_to_db(data):
    if use_mock_data:
        parking_sessions = load_data(MOCK_PARKING_SESSIONS)
        parking_sessions.append(data)
        return save_data(MOCK_PARKING_SESSIONS, data)
    save_json_to_db("parking_sessions", data)


def delete_parking_session_from_db(session_id: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM parking_sessions WHERE id == ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.OperationalError as e:
        print(f"Error deleting session: {e}")
        return False


# find a parking session ID by parking lot and license plate
def find_parking_session_id_by_plate(parking_lot_id: str, licenseplate: str = "TEST-PLATE") -> Optional[str]:
    if use_mock_data:
        sessions = load_data(MOCK_PARKING_SESSIONS)
        for session in sessions:
            if (
                session.get("parking_lot_id") == parking_lot_id
                and session.get("licenseplate") == licenseplate
            ):
                return session.get("id")
        return None
    
    all_sessions = load_json_from_db("parking_sessions")
    for session in all_sessions:
        if (
            session.get("parking_lot_id") == parking_lot_id
            and session.get("licenseplate") == licenseplate
        ):
            return session.get("id")
    
    return None