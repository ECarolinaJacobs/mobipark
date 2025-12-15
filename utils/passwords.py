import hashlib
import bcrypt

def hash_password_bcrypt(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_bcrypt(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

def verify_md5(plain: str, hashed_md5: str) -> bool:
    return hashlib.md5(plain.encode()).hexdigest() == hashed_md5
