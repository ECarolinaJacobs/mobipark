from fastapi import FastAPI
from endpoints.auth import router as auth_router

app = FastAPI()

# This is auth router imported from endpoints
# folder. Prefix is the grouping of the endpoint
# this is only necessary for auth to group them
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the API!"}