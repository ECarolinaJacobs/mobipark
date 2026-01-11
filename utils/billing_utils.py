from typing import List, Dict

from utils.storage_utils import (
    load_parking_lot_data,
    load_parking_sessions_data_from_db,
    load_payment_data_from_db
)
from utils.session_calculator import generate_payment_hash


def get_user_session_by_username(username: str) -> List[Dict]:
    sessions: List[Dict] = []

    parking_lots = load_parking_lot_data() or []

    for lot in parking_lots:
        lot_id = lot.get("id")
        if not lot_id:
            continue

        lot_sessions = load_parking_sessions_data_from_db(lot_id) or {}

        for session in lot_sessions.values():
            if session.get("user") == username:
                sessions.append(session)

    return sessions


def format_billing_record(sessions: List[Dict]) -> List[Dict]:
    billing_data = []

    parking_lots = load_parking_lot_data() or []
    payments = load_payment_data_from_db() or []

    parking_lot_index = {
        str(lot["id"]): lot for lot in parking_lots
    }

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

        transaction_hash = generate_payment_hash(session_id, session)

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
