from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.crud.mh_categories import create_card_detail_from_json, create_card_mh_categories, create_mh_category
from app.postgres.database import get_db

router = APIRouter(prefix="/mh-categories", tags=["Mental health categories"])


@router.post("/create")
def creates_a_new_mental_health_category(
    name: str = Form(..., description="Name of mental health category"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    return create_mh_category(db=db, category_name=name)


@router.post("/convert")
def converts_json_into_card_detail(
    data: List[Dict[str, Any]],
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    return create_card_detail_from_json(db=db, data=data)


@router.post("/create-card-mh-categories")
def converts_json_into_card_mh_categories(
    data: List[Dict[str, Any]],
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    return create_card_mh_categories(db=db, data=data)
