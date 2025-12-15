from fastapi import APIRouter, Header, HTTPException, status
from utils.session_manager import get_session, add_session
from utils.storage_utils import load_user_data, save_user_data
from utils.passwords import hash_password_bcrypt
from models.profile_model import ProfileUpdateRequest

router = APIRouter()

@router.get("/profile")
def get_profile(authorization: str = Header(None)):
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

    return session_user


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
        (u for u in users if u.get("username") == session_user.get("username")),
        None
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if update_data.name:
        user["name"] = update_data.name

    if update_data.password:
        user["password"] = hash_password_bcrypt(update_data.password)
        user["hash_type"] = "bcrypt"

    save_user_data(users)

    session_user.update(user)

    return {"message": "User updated successfully"}
