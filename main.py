from fastapi import FastAPI
from endpoints.auth import router as auth_router
from endpoints.payments_endpoint import router as payment_router
from endpoints.vehicles_endpoint import router as vehicle_router
from endpoints.parking_lots import router as parking_lots_router


app = FastAPI()

# This is auth router imported from endpoints
# folder. Prefix is the grouping of the endpoint
# this is only necessary for auth to group them
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

app.include_router(payment_router)
app.include_router(auth_router)
app.include_router(vehicle_router)
app.include_router(parking_lots_router)





@app.get("/")
def read_root():
    return {"message": "Welcome to the API!"}
