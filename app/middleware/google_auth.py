from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Security scheme using OAuth2 with Password Bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Function to get credentials from token
def get_credentials(token: str = Depends(oauth2_scheme)):
    try:
        creds = Credentials(token)
        # Refresh token if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials") from None
