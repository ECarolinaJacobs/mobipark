from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
def login(username: str, password: str):
    return {"message": f"User {username} logged in"}

@router.post("/register")
def register(username: str, password: str):
    return {"message": f"User {username} registered"}

@router.post("/logout")
def logout():
    return {"message": "User logged out"}
