from fastapi import APIRouter, Header, HTTPException, status
from utils.session_manager import get_session
from utils.storage_utils import (
    get_user_data_by_username,
    update_existing_user_in_db
)
from utils.passwords import hash_password_bcrypt
from models.profile_model import ProfileUpdateRequest, ProfileResponse


router = APIRouter()

@router.get("/profile", response_model=ProfileResponse)
def get_profile(authorization: str = Header(None)):
    """
    Retrieve the profile information of the authenticated user.
    authorization: Session token (required in header)
    
    Return complete profile information including:
    - User ID
    - Username
    - Name
    - Email
    - Phone
    - Role
    - Created timestamp
    - Birth year
    - Active status
    """
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
    """
    Update the profile information of the authenticated user.
    
    authorization: Session token (required in header)
    update_data: Profile fields to update (all fields are optional)
    
    Updatable fields:
    name: User's full name
    email: User's email address
    phone: User's phone number
    birth_year: User's birth year
    password: New password (will be securely hashed)
    
    Return a success message upon successful update.
    """
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

    user = get_user_data_by_username(session_user["username"]) 
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update user fields if they aree provided
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

    try:
        update_existing_user_in_db(session_user["username"], user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )

    return {"message": "Profile updated successfully"}
