from fastapi import APIRouter, HTTPException, Header, status
from utils.session_manager import get_session
from utils import billing_utils
router = APIRouter()


# for user billing info
@router.get("/billing")
def get_user_billing(Authorization: str = Header(None)):
    session_user = get_session(Authorization)
    if not session_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized: Invalid or missing session token")
    
    username = session_user["username"]

    try:
        sessions = billing_utils.get_user_session_by_username(username)
        return billing_utils.format_billing_record(sessions)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"An error occurred: {str(e)}")


# for admin to get other users billing info
@router.get("/billing/{username}")
def get_user_billing_admin(username: str, Authorization: str = Header(None)):
    token = Authorization
    session_user = get_session(token)
    if not session_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized: Invalid or missing session token")
    
    if session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not an admin, access denied!")

    try:
        sessions = billing_utils.get_user_session_by_username(username)
        return billing_utils.format_billing_record(sessions)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=F"an error occured {str(e)}")    
    
