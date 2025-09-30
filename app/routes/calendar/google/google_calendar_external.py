import logging
from datetime import datetime, timedelta
from typing import Optional

import requests
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.constants import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
from app.middleware.google_auth import get_credentials
from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.crud.card import create_user_cards_from_events
from app.postgres.crud.external_token import (
    create_external_token,
    update_external_token,
)
from app.postgres.crud.google_calendar import create_events
from app.postgres.database import get_db
from app.postgres.models.external_token import TokenCreate

router = APIRouter(prefix="/calendar/google/external", tags=["Google calendar external endpoints"])

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"

# initiates logger
log = logging.getLogger(__name__)


@router.get("/login")
async def login_google(access_token: str = Depends(JWTBearer())):
    return {
        "url": f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email%20{CALENDAR_SCOPE}&access_type=offline&state={access_token}&prompt=login"
    }


@router.get("/auth")
async def auth_google(code: str, state: str, db: Session = Depends(get_db)):
    try:
        token = decodeJWT(state)
        user_id = token["user_id"]
        token_url = "https://accounts.google.com/o/oauth2/token"
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        response = requests.post(token_url, data=data)

        if response.status_code == 200:
            response_data = response.json()
            current_datetime = datetime.now()
            expiration_delta = timedelta(seconds=response_data["expires_in"])
            expires_at = current_datetime + expiration_delta
            new_google_account = True

            google_token_types = ["access"]
            if "refresh_token" in response_data:
                google_token_types.append("refresh")

            for token_type in google_token_types:
                try:
                    update_external_token(
                        db=db,
                        user_id=user_id,
                        service_name="Google Calendar",
                        token_type=token_type,
                        token_value=response_data[f"{token_type}_token"],
                        expires_at=expires_at if token_type == "access" else None,
                    )
                except HTTPException:
                    # Create a new token if google access or refresh tokens don't already exist in db
                    create_external_token(
                        db,
                        TokenCreate(
                            user_id=user_id,
                            service_name="Google Calendar",
                            token_type=token_type,
                            token_value=response_data[f"{token_type}_token"],
                            expires_at=expires_at if token_type == "access" else None,
                        ),
                    )
                    new_google_account = True

            if new_google_account:
                creds = Credentials(token=response_data["access_token"])

                time_max = datetime.now()
                time_min = time_max - timedelta(days=30)

                # Get event log from google calendar
                event_log = await get_events_range(creds=creds, time_min=time_min, time_max=time_max)
                created_events = create_events(events=event_log, user_id=user_id, db=db)
                create_user_cards_from_events(events=created_events, user_id=user_id, db=db)

        return "success"

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error retrieving google auth tokens: {e}") from None


@router.get("/google/events")
async def get_events(creds: Credentials = Depends(get_credentials)):
    try:
        service = build("calendar", "v3", credentials=creds)
        events_result = service.events().list(calendarId="primary").execute()
        events = events_result.get("items", [])
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving events: {e}") from None


@router.get("/events-range")
async def get_events_range(
    creds: Credentials = Depends(get_credentials),
    time_min: datetime = Query(..., description="Lower bound (exclusive) for an event's start time"),
    time_max: datetime = Query(..., description="Upper bound (exclusive) for an event's end time"),
    max_results: Optional[int] = Query(..., description="Maximum number of events"),
):
    try:
        service = build("calendar", "v3", credentials=creds)
        time_min_str = time_min.isoformat() + "Z"
        events_result = service.events().list(calendarId="primary", timeMin=time_min_str).execute()
        events = events_result.get("items", [])
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving events: {e}") from None
