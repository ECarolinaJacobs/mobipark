from typing import List, Dict

from utils.storage_utils import (
    load_parking_lot_data,
    load_parking_sessions_data_from_db,
    load_payment_data_from_db
)
from utils.session_calculator import generate_payment_hash

def get_user_session_by_username(username: str) -> List[Dict]:
    all_sessions = load_parking_sessions_data_from_db() or []
    
    sessions = [s for s in all_sessions if s.get("user") == username]
    return sessions

def format_billing_record(sessions: List[Dict]) -> List[Dict]:
    billing_data = []

    parking_lots = load_parking_lot_data() or []
    payments = load_payment_data_from_db() or []

    lots_iterable = parking_lots.values() if isinstance(parking_lots, dict) else parking_lots
    parking_lot_index = {str(lot.get("id")): lot for lot in lots_iterable}

    for session in sessions:
        parking_lot = parking_lot_index.get(str(session.get("parking_lot_id")))
        if not parking_lot:
            continue

        duration_minutes = session.get("duration_minutes", 0)
        hours = round(duration_minutes / 60, 2)
        days = int(hours // 24)

        session_id = str(session.get("id"))

        amount_paid = sum(
            p.get("amount", 0)
            for p in payments
            if p.get("session_id") == session_id
        )

        transaction_hash = generate_payment_hash()

        billing_data.append({
            "session": {
                "license_plate": session.get("licenseplate"),
                "started": session.get("started"),
                "stopped": session.get("stopped"),
                "hours": hours,
                "days": days
            },
            "parking": {
                "name": parking_lot.get("name"),
                "location": parking_lot.get("location"),
                "tariff": parking_lot.get("tariff"),
                "daytariff": parking_lot.get("daytariff")
            },
            "amount": session.get("cost") or 0,
            "thash": transaction_hash,
            "payed": amount_paid,
            "balance": (session.get("cost") or 0) - amount_paid
        })

    return billing_data
