import time
from typing import Dict

import jwt
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.constants import JWT_ALGORITHM, SECRET_KEY


def auth_token_response(token: str):
    return {"auth_token": token}


def refresh_token_response(token: str):
    return {"refresh_token": token}


def sign_auth_token(user_id: str) -> Dict[str, str]:
    payload = {
        "user_id": user_id,
        "action": "auth",
        "expires": time.time() + (3600 * 1),  # Expiration time (1 hour, 3600 * 1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return auth_token_response(token)


def sign_refresh_token(user_id: str) -> Dict[str, str]:
    payload = {
        "user_id": user_id,
        "action": "refresh",
        "expires": time.time() + (3600 * 24 * 30),  # Expiration time (1 month, 3600 * 24 * 30)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return refresh_token_response(token)


def sign_reset_password_token(user_id: str) -> Dict[str, str]:
    payload = {
        "user_id": user_id,
        "action": "reset_password",
        "expires": time.time() + (3600 * 1),  # Expiration time (1 hour)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=JWT_ALGORITHM)
        if decoded_token["expires"] < time.time():
            raise jwt.ExpiredSignatureError("Token has expired")

        return decoded_token

    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if not self.verify_jwt(credentials.credentials):
            raise HTTPException(status_code=403, detail="Invalid token or expired token.")
        return credentials.credentials

    def verify_jwt(self, jwt: str) -> bool:
        isTokenValid: bool = False
        payload = None

        payload = decodeJWT(jwt)
        if payload and payload["action"] == "auth":
            isTokenValid = True
        return isTokenValid


class JWTRefreshBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTRefreshBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTRefreshBearer, self).__call__(request)
        if not self.verify_jwt(credentials.credentials):
            raise HTTPException(status_code=403, detail="Invalid token or expired token.")
        return credentials.credentials

    def verify_jwt(self, jwt: str) -> bool:
        isTokenValid: bool = False
        payload = None

        payload = decodeJWT(jwt)
        if payload and payload["action"] == "refresh":
            isTokenValid = True
        return isTokenValid
