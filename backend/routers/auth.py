from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from google.oauth2 import id_token
from google.auth.transport import requests
from datetime import datetime
import os
import hmac
import hashlib
import secrets
import database

router = APIRouter()


class GoogleLoginRequest(BaseModel):
    token: str


class EmailRegisterRequest(BaseModel):
    email: EmailStr
    password: str


class EmailLoginRequest(BaseModel):
    email: EmailStr
    password: str


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()

    return f"{salt}${password_hash}"


def verify_password(password: str, stored_password: str) -> bool:
    try:
        salt, password_hash = stored_password.split("$", 1)

        check_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        ).hex()

        return hmac.compare_digest(check_hash, password_hash)
    except Exception:
        return False


def validate_password(password: str):
    if len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters",
        )


def merge_auth_provider(current_provider, new_provider: str) -> str:
    providers = set()

    if current_provider:
        for provider in str(current_provider).split(","):
            provider = provider.strip()
            if provider:
                providers.add(provider)

    providers.add(new_provider)

    return ",".join(sorted(providers))


def user_response(user_id: str, email: str, picture=None):
    return {
        "user_id": user_id,
        "email": email,
        "picture": picture,
    }


@router.post("/register")
def register(data: EmailRegisterRequest):
    if database.users_col is None:
        raise HTTPException(status_code=500, detail="Database not connected yet")

    email = data.email.strip().lower()
    password = data.password.strip()

    validate_password(password)

    existing_user = database.users_col.find_one({"email": email})

    if existing_user:
        if existing_user.get("password_hash"):
            raise HTTPException(
                status_code=409,
                detail="Email already registered. Please sign in.",
            )

        database.users_col.update_one(
            {"_id": existing_user["_id"]},
            {
                "$set": {
                    "password_hash": hash_password(password),
                    "auth_provider": merge_auth_provider(
                        existing_user.get("auth_provider"),
                        "email",
                    ),
                    "last_login_at": datetime.utcnow(),
                }
            },
        )

        return user_response(
            str(existing_user["_id"]),
            existing_user["email"],
            existing_user.get("picture"),
        )

    result = database.users_col.insert_one(
        {
            "email": email,
            "password_hash": hash_password(password),
            "auth_provider": "email",
            "created_at": datetime.utcnow(),
            "last_login_at": datetime.utcnow(),
        }
    )

    return user_response(str(result.inserted_id), email)


@router.post("/email-login")
def email_login(data: EmailLoginRequest):
    if database.users_col is None:
        raise HTTPException(status_code=500, detail="Database not connected yet")

    email = data.email.strip().lower()
    password = data.password.strip()

    user = database.users_col.find_one({"email": email})

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password. Please sign up first.",
        )

    password_hash = user.get("password_hash")

    if not password_hash:
        raise HTTPException(
            status_code=409,
            detail="This email was created with Google. Click Sign up once to add a password, or continue with Google.",
        )

    if not verify_password(password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    database.users_col.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login_at": datetime.utcnow()}},
    )

    return user_response(
        str(user["_id"]),
        user["email"],
        user.get("picture"),
    )


@router.post("/login")
def login(data: GoogleLoginRequest):
    if database.users_col is None:
        raise HTTPException(status_code=500, detail="Database not connected yet")

    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()

    if not google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID is not configured")

    try:
        idinfo = id_token.verify_oauth2_token(
            data.token,
            requests.Request(),
            google_client_id,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = (idinfo.get("email") or "").strip().lower()
    email_verified = bool(idinfo.get("email_verified"))
    picture = idinfo.get("picture")
    name = idinfo.get("name")

    if not email:
        raise HTTPException(status_code=401, detail="Google account email not found")

    if not email_verified:
        raise HTTPException(status_code=401, detail="Google email is not verified")

    user = database.users_col.find_one({"email": email})

    if not user:
        result = database.users_col.insert_one(
            {
                "email": email,
                "google_sub": idinfo.get("sub"),
                "name": name,
                "picture": picture,
                "auth_provider": "google",
                "created_at": datetime.utcnow(),
                "last_login_at": datetime.utcnow(),
            }
        )

        return user_response(str(result.inserted_id), email, picture)

    database.users_col.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "google_sub": idinfo.get("sub"),
                "name": name,
                "picture": picture,
                "auth_provider": merge_auth_provider(
                    user.get("auth_provider"),
                    "google",
                ),
                "last_login_at": datetime.utcnow(),
            }
        },
    )

    return user_response(str(user["_id"]), email, picture)