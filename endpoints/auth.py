from fastapi import APIRouter, Response, HTTPException, status
from utils.session_manager import add_session, remove_session, get_session
from utils.storage_utils import load_user_data_from_db, save_user_data_to_db
import uuid, hashlib, secrets
from models.auth_model import LoginRequest, RegisterRequest, User

router = APIRouter()

@router.post("/login")
def login(login_data: LoginRequest, response: Response):
    username = login_data.username
    password = login_data.password
    
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing credentials"
        )

    hashed_password = hashlib.md5(password.encode()).hexdigest()
    users = load_user_data_from_db()
    
    for user in users:
        if user.get("username") == username and user.get("password") == hashed_password:
            token = str(uuid.uuid4())
            add_session(token, user)
            response.headers["Authorization"] = f"{token}"
            return {
                "message": "User logged in",
                "session_token": token
            }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

@router.post("/register")
def register(register_data: RegisterRequest, response: Response):
    username = register_data.username
    password = register_data.password
    name = register_data.name
    
    
    if not username or not password or not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing credentials"
        )
    
    users = load_user_data_from_db()
    
    if any(user.get("username") == username for user in users):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    hashed_password = hashlib.md5(password.encode()).hexdigest()
    
    new_user = User(
        id=str(uuid.uuid4()),
        username= username,
        password=hashed_password,
        name=name,
        role="USER"
    ).model_dump()
    
    

    
    
    # Save user to database
    users.append(new_user)
    
    save_user_data_to_db(users)
    
    token = str(uuid.uuid4())
    add_session(token, new_user)
    
    response.headers["Authorization"] = f"{token}"
    
    return {
        "message": f"User {username} registered",
        "session_token": token
    }
    

@router.post("/logout")
def logout(token: str):
    user = remove_session(token)
    if user:
        return {"message": "User logged out"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No active session found"
    )
