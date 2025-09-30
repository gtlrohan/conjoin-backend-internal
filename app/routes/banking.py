import logging

import requests
from fastapi import APIRouter, Depends, HTTPException

from app.middleware.jwt import JWTBearer

router = APIRouter(prefix="/banking", tags=["Banking API's"])

# initiates logger
log = logging.getLogger(__name__)


@router.get("/starling/get_account")
def get_profile(bearer_token: str, access_token: str = Depends(JWTBearer())):
    """
    Retrieves the bank balance of a Starling bank account
    """
    url = "https://api-sandbox.starlingbank.com/api/v2/accounts"
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {bearer_token}"}

    try:
        response = requests.get(url, headers=headers)
        return response.json()

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.get("/starling/get_balance")
def get_balance(account_uid: str, bearer_token: str, access_token: str = Depends(JWTBearer())):
    """
    Retrieves the bank balance of a Starling bank account
    """
    url = f"https://api-sandbox.starlingbank.com/api/v2/accounts/{account_uid}/balance"
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {bearer_token}"}

    try:
        response = requests.get(url, headers=headers)
        return response.json()

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.get("/starling/get_spending_category")
def get_spending_category(account_uid: str, year: str, month: str, bearer_token: str, access_token: str = Depends(JWTBearer())):
    """
    Retrieves the spending categories of a Starling bank account
    """
    url = f"https://api-sandbox.starlingbank.com/api/v2/accounts/{account_uid}/spending-insights/spending-category"
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {bearer_token}"}
    params = {
        "year": year,
        "month": month,
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json()

    except HTTPException as e:
        raise e  # Reraise the HTTPException
