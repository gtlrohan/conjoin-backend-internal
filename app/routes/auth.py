from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from app.middleware.jwt import (
    JWTRefreshBearer,
    decodeJWT,
    sign_auth_token,
    sign_refresh_token,
)
from app.postgres.crud.cognitive_fingerprint import create_cognitive_fingerprint
from app.postgres.crud.cognitive_score import create_cognitive_score
from app.postgres.crud.user import authenticate_user, create_user
from app.postgres.database import get_db
from app.postgres.models.user import UserCreate, UserLogin

router = APIRouter(prefix="/auth", tags=["Authorization"])


@router.post("/login")
def post_user_login(body: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, body)
    if user:
        auth_token = sign_auth_token(user.user_id)
        refresh_token = sign_refresh_token(user.user_id)
        return {"auth_token": auth_token["auth_token"], "refresh_token": refresh_token["refresh_token"]}
    raise HTTPException(status_code=403, detail="Access denied.")


@router.post("/register")
def post_user_register(body: UserCreate, db: Session = Depends(get_db)):
    user = create_user(db, body)
    cog_score = create_cognitive_score(db, user.user_id, 5.0)
    create_cognitive_fingerprint(db, user.user_id, 5, 5, 5, 5, 5)
    return {"user_id": user.user_id, "email": user.email, "password": user.password}


@router.get("/generate-auth-token")
def generate_new_auth_token(db: Session = Depends(get_db), refresh_token: str = Depends(JWTRefreshBearer())):
    token = decodeJWT(refresh_token)
    user_id = token["user_id"]
    return sign_auth_token(user_id)
