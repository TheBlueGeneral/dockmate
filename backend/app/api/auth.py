from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional

from app.supabase_client import supabase  # may be None if not configured
from app.utils.security import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# --------- Models ---------
class SignupRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

# --------- Local dev fallback when Supabase is not configured ---------
USERS_LOCAL: dict[str, str] = {}  # username -> password_hash
USE_SUPABASE = supabase is not None


def _signup_local(username: str, password: str):
    if username in USERS_LOCAL:
        raise HTTPException(status_code=400, detail="Username already exists")
    USERS_LOCAL[username] = hash_password(password)

def _login_local(username: str, password: str):
    pwd_hash = USERS_LOCAL.get(username)
    if not pwd_hash or not verify_password(password, pwd_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    # sub can be the username in local mode
    token = create_access_token({"sub": username, "username": username})
    return token

def _signup_supabase(username: str, password: str):
    # check existing
    existing = supabase.table("users").select("id, username").eq("username", username).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Username already exists")

    pwd_hash = hash_password(password)
    inserted = supabase.table("users").insert({"username": username, "password": pwd_hash}).execute()
    if not inserted.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

def _login_supabase(username: str, password: str):
    res = supabase.table("users").select("*").eq("username", username).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    user = res.data[0]
    # Your table might store "password" or "password_hash" — try both
    stored_hash = user.get("password_hash") or user.get("password")
    if not stored_hash or not verify_password(password, stored_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Use numeric/string id from DB as sub
    sub = user.get("id") or user.get("username")
    token = create_access_token({"sub": sub, "username": user.get("username")})
    return token


# --------- Routes ---------
@router.post("/signup")
def signup(data: SignupRequest):
    if USE_SUPABASE:
        _signup_supabase(data.username, data.password)
    else:
        _signup_local(data.username, data.password)
    return {"message": "User created"}

@router.post("/login")
def login(data: LoginRequest):
    if USE_SUPABASE:
        token = _login_supabase(data.username, data.password)
    else:
        token = _login_local(data.username, data.password)
    return {"access_token": token, "token_type": "bearer"}

# Token-protected helper used by other modules
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {"sub": current_user.get("sub"), "username": current_user.get("username")}
