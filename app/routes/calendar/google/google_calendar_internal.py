import logging

from fastapi import APIRouter

router = APIRouter(prefix="/calendar/google/internal", tags=["Google calendar internal endpoints"])


# initiates logger
log = logging.getLogger(__name__)
