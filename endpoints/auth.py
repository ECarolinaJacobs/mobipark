from fastapi import APIRouter, Response, HTTPException, status, Header
from utils.session_manager import add_session, remove_session, get_session
from utils.storage_utils import load_user_data, save_user_data
import uuid, hashlib, secrets
from utils.passwords import hash_password_bcrypt, verify_bcrypt, verify_md5
from models.auth_model import LoginRequest, RegisterRequest, User
from models.hotel_manager_model import HotelManagerCreate
from models.profile_model import ProfileResponse, ProfileUpdateRequest
import datetime

router = APIRouter()


@router.post("/login")
def login(login_data: LoginRequest, response: Response):
    username = login_data.username
    password = login_data.password

    if not username or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credentials")

    users = load_user_data()
    for user in users:
        if user.get("username") != username:
            continue

        hash_type = user.get("hash_type", "md5")
        stored_pw = user.get("password", "")

        if hash_type == "bcrypt":
            if verify_bcrypt(password, stored_pw):
                token = str(uuid.uuid4())
                add_session(token, user)
                response.headers["Authorization"] = token
                return {"message": "User logged in", "session_token": token}
            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if hash_type == "md5":
            if verify_md5(password, stored_pw):
                # after the usser successfuly logs in with old md5 it upgrades to bcrypt
                new_hash = hash_password_bcrypt(password)
                user["password"] = new_hash
                user["hash_type"] = "bcrypt"
                save_user_data(users)

                token = str(uuid.uuid4())
                add_session(token, user)
                response.headers["Authorization"] = token
                return {"message": "User logged in (password upgraded to bcrypt)", "session_token": token}

            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.post("/register")
def register(register_data: RegisterRequest, response: Response, authorization: str = Header(None)):
    username = register_data.username
    password = register_data.password
    name = register_data.name
    role = register_data.role.upper() if register_data.role else "USER"

    email = register_data.email or ""
    phone = register_data.phone or ""
    birth_year = register_data.birth_year

    if not username or not password or not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credentials")

    if role == "ADMIN":
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authorization required"
            )
        admin_user = get_session(authorization)
        if not admin_user or admin_user.get("role") != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create admin accounts"
            )

    users = load_user_data()
    if any(user.get("username") == username for user in users):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    hashed_password = hash_password_bcrypt(password)

    new_user = User(
        id=str(uuid.uuid4()),
        username=username,
        password=hashed_password,
        hash_type="bcrypt",
        name=name,
        email=email,
        phone=phone,
        role=role,
        created_at=str(datetime.now()),
        birth_year=birth_year,
        active=True,
        managed_parking_lot_id=register_data.managed_parking_lot_id
    ).model_dump()

    new_user["hash_type"] = "bcrypt"

    users.append(new_user)
    save_user_data(users)

    token = str(uuid.uuid4())
    add_session(token, new_user)
    response.headers["Authorization"] = token

    return {"message": f"User {username} registered", "session_token": token}


@router.post("/register/hotel-manager")
def register_hotel_manager(hotel_manager_data: HotelManagerCreate, authorization: str = Header(None)):
    """admin only endpoint to create a hotel manager account and assign them a parking lot"""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authorization required")
    admin_user = get_session(authorization)
    if not admin_user or admin_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create hotel manager accounts"
        )
    from utils.storage_utils import load_parking_lot_data

    parking_lots = load_parking_lot_data()
    if isinstance(parking_lots, dict):
        lot_exists = hotel_manager_data.parking_lot_id in parking_lots
    else:
        lot_exists = any(lot.get("id") == hotel_manager_data.parking_lot_id for lot in parking_lots)

    if not lot_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parking lot with Id {hotel_manager_data.parking_lot_id} not found",
        )
    users = load_user_data()
    if any(user.get("username") == hotel_manager_data.username for user in users):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    hashed_password = hash_password_bcrypt(hotel_manager_data.password)
    new_hotel_manager = User(
        id=str(uuid.uuid4()),
        username=hotel_manager_data.username,
        password=hashed_password,
        name=hotel_manager_data.name,
        email=hotel_manager_data.email,
        phone=hotel_manager_data.phone,
        role="HOTEL_MANAGER",
        managed_parking_lot_id=hotel_manager_data.parking_lot_id,
    ).model_dump()
    new_hotel_manager["hash_type"] = "bcrypt"
    users.append(new_hotel_manager)
    save_user_data(users)
    return {
        "message": f"Hotel manager {hotel_manager_data.username} created successfully",
        "username": hotel_manager_data.username,
        "managed_parking_lot_id": hotel_manager_data.parking_lot_id,
    }


@router.post("/logout")
def logout(token: str):
    user = remove_session(token)
    if user:
        return {"message": "User logged out"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session found")
