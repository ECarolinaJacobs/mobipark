from datetime import datetime
from utils.storage_utils import load_payment_data
from hashlib import md5
import math
import uuid


def calculate_price(parkinglot, sid, data):
    price = 0
    start = datetime.fromisoformat(data["started"])

    if data.get("stopped"):
        end = datetime.fromisoformat(data["stopped"])
    else:
        end = datetime.now()

    diff = end - start
    hours = math.ceil(diff.total_seconds() / 3600)

    if diff.total_seconds() < 180:
        price = 0
    elif end.date() > start.date():
        price = float(parkinglot.get("daytariff", 999)) * (diff.days + 1)
    else:
        price = float(parkinglot.get("tariff")) * hours

        if price > float(parkinglot.get("daytariff", 999)):
            price = float(parkinglot.get("daytariff", 999))

    return (price, hours, diff.days + 1 if end.date() > start.date() else 0)


def generate_payment_hash():
    return str(uuid.uuid4())



def generate_transaction_validation_hash():
    return str(uuid.uuid4())


def check_payment_amount(hash):
    payments = load_payment_data()
    total = 0

    for payment in payments:
        if payment["transaction"] == hash:
            total += payment["amount"]

    return total

