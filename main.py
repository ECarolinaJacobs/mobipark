from fastapi import FastAPI

from endpoints.auth import router as auth_router
from endpoints.billing_endpoint import router as billing_router
from endpoints.parking_lots import router as parking_lots_router
from endpoints.payments_endpoint import router as payment_router
from endpoints.refunds_endpoint import router as refunds_router
from endpoints.profile_endpoint import router as profile_router
from endpoints.hotel_manager_endpoint import router as hotel_manager_router
from endpoints.reservations import router as reservations_router
from endpoints.vehicles_endpoint import router as vehicle_router
from utils.storage_utils import init_db
from dotenv import load_dotenv
from scripts.insert_hash import start


load_dotenv()
init_db()
# start()
app = FastAPI()

# This is auth router imported from endpoints
# folder. Prefix is the grouping of the endpoint
# this is only necessary for auth to group them
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

app.include_router(payment_router)
app.include_router(auth_router)
app.include_router(vehicle_router)
app.include_router(parking_lots_router)
app.include_router(billing_router)
app.include_router(refunds_router)

app.include_router(reservations_router)
app.include_router(profile_router)
app.include_router(hotel_manager_router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the API!"}
