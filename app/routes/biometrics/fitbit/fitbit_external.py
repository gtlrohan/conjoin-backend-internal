import base64
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import requests
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
)
from sqlalchemy.orm import Session

from app.constants import (
    CODE_VERIFIER,
    FITBIT_CLIENT_ID,
    FITBIT_CLIENT_SECRET,
    FITBIT_REDIRECT_URI,
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.crud.external_token import (
    create_external_token,
    retrieve_external_token,
    update_external_token,
)
from app.postgres.crud.fitbit_heart import create_heart_log
from app.postgres.crud.fitbit_sleep import (
    create_sleep_log,
    retrieve_users_last_sleep,
)
from app.postgres.database import get_db
from app.postgres.models.external_token import TokenCreate, TokenRetrieve

router = APIRouter(prefix="/biometrics/fitbit/external", tags=["External Fitbit APIs"])

# initiates logger
log = logging.getLogger(__name__)


@router.get("/subscriber")
async def fitbit_subscriber_verifier(verify: str):
    """
    Verifies the fitbit subscriber
    """
    correct_verfication_code = "9b9fa329cd4d4d7c892383ef15802d5c89919e74be603c8c24938c87a3f20ac1"

    if verify == correct_verfication_code:
        return Response(status_code=204)
    else:
        raise HTTPException(status_code=404, detail="Verification code is incorrect") from None


@router.post("/subscriber")
async def fitbit_subscriber_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Picks up the changes in the subscribed data
    """
    try:
        body = await request.json()
        print("Received body: ", body)

        if not body:
            return Response(status_code=204)

        # Schedule the background task
        background_tasks.add_task(process_fitbit_data, body, db)

        return Response(status_code=204)

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"{e}") from None


async def process_fitbit_data(body: list, db: Session):
    try:
        user_id = body[0]["subscriptionId"]

        # retrieve users access_token
        access_token_obj = retrieve_external_token(db, TokenRetrieve(user_id=user_id, service_name="Fitbit", token_type="access"))
        access_token = access_token_obj.token_value

        # check if token is out of date and if so generate new token
        if not access_token_obj.expires_at or access_token_obj.expires_at < datetime.now(timezone.utc):
            refresh_token_obj = retrieve_external_token(db, TokenRetrieve(user_id=user_id, service_name="Fitbit", token_type="refresh"))
            # get new access_token if out of date
            access_token = await get_new_fitbit_auth_token_using_refresh(user_id=user_id, refresh_token=refresh_token_obj.token_value, db=db)

        # loops through all collections that have changed
        for collection in body:
            # check if sleep has changed
            if collection["collectionType"] == "sleep":
                # retrieve user's last sleep record and date
                last_sleep_record = retrieve_users_last_sleep(user_id=user_id, db=db)
                last_sleep_record_date = last_sleep_record.date_of_sleep if last_sleep_record else None

                # Calculate the start date (the day after the last sleep record)
                if last_sleep_record_date:
                    start_date = (last_sleep_record_date + timedelta(days=1)).strftime("%Y-%m-%d")
                else:
                    start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")  # Default to 30 days ago if no records found

                # Set the end date to today
                end_date = datetime.utcnow().strftime("%Y-%m-%d")

                # Retrieve all sleep data for the user from the start date to today
                if start_date <= end_date:
                    sleep_log = await get_sleep_logs_by_date_range(start_date=start_date, end_date=end_date, token=access_token)
                    create_sleep_log(sleep_logs=sleep_log, user_id=user_id, db=db)

                # Since subscriber only gives updates about activity, weight, nutrition and sleep
                # want to update the users heart log everytime sleep gets updated
                # COME BACK TO THIS LATER

    except Exception as e:
        # Handle exception, maybe log it
        # (as parent function would have already returned response due to this being a background task)
        print(f"Error processing Fitbit data: {e}")


async def get_new_fitbit_auth_token_using_refresh(user_id: str, refresh_token: str, db: Session = Depends(get_db)):
    try:
        token_url = "https://api.fitbit.com/oauth2/token"
        client_credentials = f"{FITBIT_CLIENT_ID}:{FITBIT_CLIENT_SECRET}"
        encoded_client_credentials = base64.b64encode(client_credentials.encode()).decode("utf-8")
        headers = {"Authorization": f"Basic {encoded_client_credentials}"}
        data = {"client_id": FITBIT_CLIENT_ID, "code_verifier": CODE_VERIFIER, "grant_type": "refresh_token", "refresh_token": refresh_token}
        response = requests.post(token_url, data=data, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            current_datetime = datetime.now()
            expiration_delta = timedelta(seconds=response_data["expires_in"])
            expires_at = current_datetime + expiration_delta

            fitbit_token_types = ["access", "refresh"]

            for token_type in fitbit_token_types:
                try:
                    update_external_token(
                        db=db,
                        user_id=user_id,
                        service_name="Fitbit",
                        token_type=token_type,
                        token_value=response_data[f"{token_type}_token"],
                        expires_at=expires_at if token_type == "access" else None,
                    )
                except HTTPException as e:
                    raise HTTPException(status_code=404, detail=f"external token not found: {e}") from None

            return response_data["access_token"]

        else:
            print(response.text)
            raise HTTPException(status_code=response.status_code, detail=response.json())

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error retrieving fitbit auth tokens: {e}") from None


@router.post("/subscriber/create")
async def create_subscription_for_users_fitbit_data(fitbit_token: str, access_token: str = Depends(JWTBearer())):
    """
    Creates a subscription for the user, so it will then notify when there are updates to that users data
    The user_id is used as the users fitbit subscription_id (the subscription_id is used to identify subscriptions)
    """
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    try:
        url = f"https://api.fitbit.com/1/user/-/apiSubscriptions/{user_id}.json"
        headers = {"Authorization": f"Bearer {fitbit_token}", "Content-Length": "0"}
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise HTTPException(status_code=401, detail="The request requires user authentication.")
        elif response.status_code == 403:
            raise HTTPException(status_code=403, detail="The server understood the request, but is refusing to fulfill it.")
        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error creating subscription for user {user_id}: {e}") from None


@router.post("/subscriber/delete")
async def delete_fitbit_subscription_for_user(fitbit_token: str, access_token: str = Depends(JWTBearer())):
    """
    Creates a subscription for the user, so it will then notify when there are updates to that users data
    The user_id is used as the users fitbit subscription_id (the subscription_id is used to identify subscriptions)
    """
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    try:
        url = f"https://api.fitbit.com/1/user/-/apiSubscriptions/{user_id}.json"
        headers = {"Authorization": f"Bearer {fitbit_token}", "Content-Length": "0"}
        response = requests.delete(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise HTTPException(status_code=401, detail="The request requires user authentication.")
        elif response.status_code == 403:
            raise HTTPException(status_code=403, detail="The server understood the request, but is refusing to fulfill it.")
        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error creating subscription for user {user_id}: {e}") from None


@router.get("/login")
async def fitbit_login(db: Session = Depends(get_db), access_token: str = Depends(JWTBearer())):
    # Calculate the SHA-256 hash of the code verifier
    sha256_verifier = hashlib.sha256(CODE_VERIFIER.encode()).digest()

    # Base64url encode the SHA-256 hash and remove any padding characters ('=')
    code_challenge = base64.urlsafe_b64encode(sha256_verifier).decode().rstrip("=")

    # Construct the authorization URL with the code challenge
    authorization_url = (
        f"https://www.fitbit.com/oauth2/authorize?"
        f"response_type=code&"
        f"client_id={FITBIT_CLIENT_ID}&"
        f"scope=activity+cardio_fitness+electrocardiogram+heartrate+location+nutrition+oxygen_saturation+profile+respiratory_rate+settings+sleep+social+temperature+weight&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256&"
        f"redirect_uri={FITBIT_REDIRECT_URI}"
        f"&state={access_token}"
    )

    return {"url": authorization_url}


@router.get("/auth")
async def auth_fitbit(code: str, state: str, db: Session = Depends(get_db)):
    # Successful Oauth2.0 login will redirect to this endpoint
    try:
        token = decodeJWT(state)
        user_id = token["user_id"]
        token_url = "https://api.fitbit.com/oauth2/token"
        client_credentials = f"{FITBIT_CLIENT_ID}:{FITBIT_CLIENT_SECRET}"
        encoded_client_credentials = base64.b64encode(client_credentials.encode()).decode("utf-8")
        headers = {"Authorization": f"Basic {encoded_client_credentials}"}
        data = {
            "client_id": FITBIT_CLIENT_ID,
            "code": code,
            "code_verifier": CODE_VERIFIER,
            "grant_type": "authorization_code",
            "redirect_uri": FITBIT_REDIRECT_URI,
        }
        response = requests.post(token_url, data=data, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            current_datetime = datetime.now()
            expiration_delta = timedelta(seconds=response_data["expires_in"])
            expires_at = current_datetime + expiration_delta
            new_fitbit_account = False

            fitbit_token_types = ["access", "refresh"]

            print(response_data["access_token"])

            for token_type in fitbit_token_types:
                try:
                    update_external_token(
                        db=db,
                        user_id=user_id,
                        service_name="Fitbit",
                        token_type=token_type,
                        token_value=response_data[f"{token_type}_token"],
                        expires_at=expires_at if token_type == "access" else None,
                    )
                except HTTPException:
                    # Create a new token if fitbit access or refresh tokens don't already exist in db
                    create_external_token(
                        db,
                        TokenCreate(
                            user_id=user_id,
                            service_name="Fitbit",
                            token_type=token_type,
                            token_value=response_data[f"{token_type}_token"],
                            expires_at=expires_at if token_type == "access" else None,
                        ),
                    )
                    new_fitbit_account = True

            # Also will want to create a subscriber for new fitbit account
            if new_fitbit_account:
                # Calculate start_date as 30 days before current_datetime
                start_date = current_datetime - timedelta(days=30)

                # Format dates in YYYY-MM-DD format for the API call
                start_date_formatted = start_date.strftime("%Y-%m-%d")
                end_date_formatted = current_datetime.strftime("%Y-%m-%d")

                # Get 30 days of sleep and heart logs from fitbit
                sleep_log = await get_sleep_logs_by_date_range(
                    start_date=start_date_formatted,
                    end_date=end_date_formatted,
                    token=response_data["access_token"],
                )
                heart_log = await get_heart_rate_time_series_date_range(
                    start_date=start_date_formatted,
                    end_date=end_date_formatted,
                    token=response_data["access_token"],
                )

                # save logs to our database
                create_sleep_log(sleep_logs=sleep_log, user_id=user_id, db=db)
                create_heart_log(heart_logs=heart_log, user_id=user_id, db=db)

                # Delete subscription for fitbit user to make sure multiple subscriptions aren't being created
                try:
                    await delete_fitbit_subscription_for_user(fitbit_token=response_data["access_token"], access_token=state)
                except Exception:
                    pass  # if theres an error do nothing as it means there was no subscription present

                # Create new subscription for fitbit user
                await create_subscription_for_users_fitbit_data(fitbit_token=response_data["access_token"], access_token=state)

            return "success"

        else:
            print(response.text)
            raise HTTPException(status_code=response.status_code, detail=response.json())

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error retrieving fitbit auth tokens: {e}") from None


@router.get(
    "/sleep/date",
    responses={
        200: {"description": "Successful request."},
        401: {"description": "The request requires user authentication."},
        403: {"description": "The server understood the request, but is refusing to fulfill it."},
        500: {"description": "Error retrieving sleep log"},
    },
)
async def get_sleep_log_by_date(
    user_id: str = "-",
    date: str = "yyyy-MM-dd",  # Date for the sleep log in the format yyyy-MM-dd
    token: str = Header(..., description="Fitbit API access token"),
    access_token: str = Depends(JWTBearer()),
):
    """
    The Get Sleep Logs by Date endpoint returns a summary and list of a user's sleep log entries (including naps) as well as detailed sleep entry data for a given day.
    """
    try:
        url = f"https://api.fitbit.com/1.2/user/{user_id}/sleep/date/{date}.json"
        headers = {"Authorization": f"Bearer {token}", "accept": "application/json", "accept-language": "en-US", "accept-locale": "en_US"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise HTTPException(status_code=401, detail="The request requires user authentication.")
        elif response.status_code == 403:
            raise HTTPException(status_code=403, detail="The server understood the request, but is refusing to fulfill it.")
        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sleep log: {e}") from None


@router.get(
    "/sleep/date-range",
    responses={
        200: {"description": "Successful request."},
        401: {"description": "The request requires user authentication."},
        403: {"description": "The server understood the request, but is refusing to fulfill it."},
        500: {"description": "Error retrieving sleep log"},
    },
)
async def get_sleep_logs_by_date_range(
    fitbit_user_id: str = "-",
    start_date: str = Query(..., description="Start date for the sleep log in the format yyyy-MM-dd"),
    end_date: str = Query(..., description="End date for the sleep log in the format yyyy-MM-dd"),
    token: str = Header(..., description="Fitbit API access token"),
    access_token: str = Depends(JWTBearer()),
):
    """
    The Get Sleep Logs by Date Range endpoint returns a list of a user's sleep log entries (including naps) as well as detailed sleep entry data for a given date range (inclusive of start and end dates).
    """
    try:
        url = f"https://api.fitbit.com/1.2/user/{fitbit_user_id}/sleep/date/{start_date}/{end_date}.json"
        headers = {"Authorization": f"Bearer {token}", "accept": "application/json", "accept-language": "en-US", "accept-locale": "en_US"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise HTTPException(status_code=401, detail="The request requires user authentication.")
        elif response.status_code == 403:
            raise HTTPException(status_code=403, detail="The server understood the request, but is refusing to fulfill it.")
        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sleep log: {e}") from None


@router.get(
    "/heart/date",
    responses={
        200: {"description": "Successful request."},
        401: {"description": "The request requires user authentication."},
        403: {"description": "The server understood the request, but is refusing to fulfill it."},
        500: {"description": "Error retrieving heart data"},
    },
)
async def get_heart_rate_time_series(
    user_id: str = "-",
    date: str = Query(..., description="The date of the period specified in the format yyyy-MM-dd or today."),
    period: str = Query(..., description="The range of which data will be returned. Options are 1d, 7d, 30d, 1w, and 1m."),
    token: str = Header(..., description="Fitbit API access token"),
    access_token: str = Depends(JWTBearer()),
):
    """
    Returns the time series data in the specified range for a given resource in the format requested using units in the unit systems that corresponds to the Accept-Language header provided.
    """
    try:
        url = f"https://api.fitbit.com/1/user/{user_id}/activities/heart/date/{date}/{period}.json"
        headers = {"Authorization": f"Bearer {token}", "accept": "application/json", "accept-language": "en-US", "accept-locale": "en_US"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()

        elif response.status_code == 401:
            raise HTTPException(status_code=401, detail="The request requires user authentication.")
        elif response.status_code == 403:
            raise HTTPException(status_code=403, detail="The server understood the request, but is refusing to fulfill it.")
        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving heart data: {e}") from None


@router.get(
    "/heart/date-range",
    responses={
        200: {"description": "Successful request."},
        401: {"description": "The request requires user authentication."},
        403: {"description": "The server understood the request, but is refusing to fulfill it."},
        500: {"description": "Error retrieving heart data"},
    },
)
async def get_heart_rate_time_series_date_range(
    user_id: str = "-",
    start_date: str = Query(..., description="The start date of the period specified in the format yyyy-MM-dd or today."),
    end_date: str = Query(..., description="The end date of the period specified in the format yyyy-MM-dd or today."),
    token: str = Header(..., description="Fitbit API access token"),
    access_token: str = Depends(JWTBearer()),
):
    """
    Returns the time series data in the specified range for a given resource in the format requested using units in the unit systems that corresponds to the Accept-Language header provided.
    """
    try:
        url = f"https://api.fitbit.com/1/user/{user_id}/activities/heart/date/{start_date}/{end_date}.json"
        headers = {"Authorization": f"Bearer {token}", "accept": "application/json", "accept-language": "en-US", "accept-locale": "en_US"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise HTTPException(status_code=401, detail="The request requires user authentication.")
        elif response.status_code == 403:
            raise HTTPException(status_code=403, detail="The server understood the request, but is refusing to fulfill it.")
        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving heart data: {e}") from None


@router.get(
    "/heart/intraday/date",
    responses={
        200: {"description": "Successful request."},
        401: {"description": "The request requires user authentication."},
        403: {"description": "The server understood the request, but is refusing to fulfill it."},
        500: {"description": "Error retrieving heart data"},
    },
)
async def get_heart_rate_intraday_time_series(
    user_id: str = "-",
    start_date: str = Query(..., description="The start date of the period specified in the format yyyy-MM-dd or today."),
    end_date: str = Query(..., description="The end date of the period specified in the format yyyy-MM-dd or today."),
    detail_level: str = Query(..., description="The number of data points to include either 1sec, 1min, 5min or 15min."),
    token: str = Header(..., description="Fitbit API access token"),
    access_token: str = Depends(JWTBearer()),
):
    """
    Returns the intraday time series for a given resource in the format requested. If your application has the appropriate access, your calls to a time series endpoint for a specific day (by using start and end dates on the same day or a period of 1d), the response will include extended intraday values with a one-minute detail level for that day. Unlike other time series calls that allow fetching data of other users, intraday data is available only for and to the authorized user.
    """
    try:
        url = f"https://api.fitbit.com/1/user/{user_id}/activities/heart/date/{start_date}/{end_date}/{detail_level}.json"
        headers = {"Authorization": f"Bearer {token}", "accept": "application/json", "accept-language": "en-US", "accept-locale": "en_US"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise HTTPException(status_code=401, detail="The request requires user authentication.")
        elif response.status_code == 403:
            raise HTTPException(status_code=403, detail="The server understood the request, but is refusing to fulfill it.")
        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving heart data: {e}") from None


@router.get(
    "/heart/intraday/date/time",
    responses={
        200: {"description": "Successful request."},
        401: {"description": "The request requires user authentication."},
        403: {"description": "The server understood the request, but is refusing to fulfill it."},
        500: {"description": "Error retrieving heart data"},
    },
)
async def get_heart_rate_intraday_time_series_time_range(
    user_id: str = "-",
    start_date: str = Query(..., description="The start date of the period specified in the format yyyy-MM-dd or today."),
    end_date: str = Query(..., description="The end date of the period specified in the format yyyy-MM-dd or today."),
    detail_level: str = Query(..., description="The number of data points to include either 1sec, 1min, 5min or 15min."),
    start_time: str = Query(..., description="The start of the period in the format of HH:mm."),
    end_time: str = Query(..., description="The end time of the period in the format of HH:mm."),
    token: str = Header(..., description="Fitbit API access token"),
    access_token: str = Depends(JWTBearer()),
):
    """
    Returns the intraday time series for a given resource in the format requested. If your application has the appropriate access, your calls to a time series endpoint for a specific day (by using start and end dates on the same day or a period of 1d), the response will include extended intraday values with a one-minute detail level for that day. Unlike other time series calls that allow fetching data of other users, intraday data is available only for and to the authorized user.
    """
    try:
        url = (
            f"https://api.fitbit.com/1/user/{user_id}/activities/heart/date/{start_date}/{end_date}/{detail_level}/time/{start_time}/{end_time}.json"
        )
        headers = {"Authorization": f"Bearer {token}", "accept": "application/json", "accept-language": "en-US", "accept-locale": "en_US"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise HTTPException(status_code=401, detail="The request requires user authentication.")
        elif response.status_code == 403:
            raise HTTPException(status_code=403, detail="The server understood the request, but is refusing to fulfill it.")
        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving heart data: {e}") from None
