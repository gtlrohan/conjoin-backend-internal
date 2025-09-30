from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

from app.postgres.models.external_token import TokenCreate, TokenRetrieve
from app.postgres.schema.external_token import ExternalToken


def create_external_token(db: Session, token: TokenCreate):
    db_token = ExternalToken(
        user_id=token.user_id,
        service_name=token.service_name,
        token_type=token.token_type,
        token_value=token.token_value,
        expires_at=token.expires_at,
    )
    db.add(db_token)
    db.commit()


def retrieve_external_token(db: Session, token_retrieve: TokenRetrieve):
    token = (
        db.query(ExternalToken)
        .filter_by(user_id=token_retrieve.user_id, service_name=token_retrieve.service_name, token_type=token_retrieve.token_type)
        .first()
    )

    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")

    return token


def update_external_token(db: Session, user_id: str, service_name: str, token_type: str, token_value: str, expires_at: datetime = None):
    try:
        token = db.query(ExternalToken).filter_by(user_id=user_id, service_name=service_name, token_type=token_type).one()

        token.token_value = token_value
        if expires_at:
            token.expires_at = expires_at

        db.commit()

    except NoResultFound:
        raise HTTPException(status_code=404, detail="Token not found for the specified service and token type") from None
