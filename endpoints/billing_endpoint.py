from fastapi import APIRouter, HTTPException, Header, status
from utils.storage_utils import load_parking_lot_data, load_json
from utils.session_manager import get_session
from utils import session_calculator as sc
router = APIRouter()


# for user billing info
@router.get("/billing")
def get_user_billing(Authorization: str = Header(None)):
    token = Authorization
    session_user = get_session(token)
    if not session_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized: Invalid or missing session token")

    data = []
    for pid, parkinglot in load_parking_lot_data().items():
        sessions = load_json(f"data/pdata/p{pid}-sessions.json")
        if not isinstance(sessions, dict):
            continue
        for sid, session in sessions.items():
            if session.get("user") == session_user["username"]:
                amount, hours, days = sc.calculate_price(parkinglot, sid, session)
                transaction = sc.generate_payment_hash()
                payed = sc.check_payment_amount(transaction)
                data.append({
                    "session": {
                        **{k: session[k] for k in ["licenseplate", "started", "stopped"] if k in session},
                        "hours": hours,
                        "days": days
                    },
                    "parking": {k: parkinglot[k] for k in ["name", "location", "tariff", "daytariff"] if k in parkinglot},
                    "amount": amount,
                    "thash": transaction,
                    "payed": payed,
                    "balance": amount - payed
                })
    return data


# for admin to get other users billing info
@router.get("/billing/{username}")
def get_user_billing_admin(username: str, Authorization: str = Header(None)):
    token = Authorization
    session_user = get_session(token)
    if not session_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized: Invalid or missing session token")
    if session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not an admin, access denied!")

    data = []
    for pid, parkinglot in load_parking_lot_data().items():
        sessions = load_json(f"data/pdata/p{pid}-sessions.json")
        if not isinstance(sessions, dict):
            continue
        for sid, session in sessions.items():
            if session.get("user") == username:
                amount, hours, days = sc.calculate_price(parkinglot, sid, session)
                transaction = sc.generate_payment_hash()
                payed = sc.check_payment_amount(transaction)
                data.append({
                    "session": {
                        **{k: session[k] for k in ["licenseplate", "started", "stopped"] if k in session},
                        "hours": hours,
                        "days": days
                    },
                    "parking": {k: parkinglot[k] for k in ["name", "location", "tariff", "daytariff"] if k in parkinglot},
                    "amount": amount,
                    "thash": transaction,
                    "payed": payed,
                    "balance": amount - payed
                })
    return data