from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TokenCreate(BaseModel):
    user_id: int
    service_name: str
    token_type: str
    token_value: str
    expires_at: Optional[datetime] = None


class TokenRetrieve(BaseModel):
    user_id: int
    service_name: str
    token_type: str
