from fastapi import APIRouter, Header, HTTPException, status
from utils.session_manager import get_session, add_session
from utils.storage_utils import load_user_data, save_user_data
from utils.passwords import hash_password_bcrypt
from models.profile_model import ProfileUpdateRequest
from models.profile_model import ProfileResponse


router = APIRouter()

@router.get("/profile", response_model=ProfileResponse)
def get_profile(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session token"
        )

    user = get_session(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token"
        )

    return {
        "id": user["id"],
        "username": user["username"],
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "role": user["role"],
        "created_at": user["created_at"],
        "birth_year": user.get("birth_year"),
        "active": user.get("active", True),
    }


@router.put("/profile")
def update_profile(
    update_data: ProfileUpdateRequest,
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session token"
        )

    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token"
        )

    users = load_user_data()
    user = next(
        (u for u in users if u["id"] == session_user["id"]),
        None
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if update_data.name is not None:
        user["name"] = update_data.name
        session_user["name"] = update_data.name

    if update_data.email is not None:
        user["email"] = update_data.email
        session_user["email"] = update_data.email

    if update_data.phone is not None:
        user["phone"] = update_data.phone
        session_user["phone"] = update_data.phone

    if update_data.birth_year is not None:
        user["birth_year"] = update_data.birth_year
        session_user["birth_year"] = update_data.birth_year

    if update_data.password is not None:
        user["password"] = hash_password_bcrypt(update_data.password)
        user["hash_type"] = "bcrypt"

    save_user_data(users)

    return {"message": "Profile updated successfully"}
