import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette_context.middleware import RawContextMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.responses import PlainTextResponse

from app.constants import ALLOWED_ORIGINS
from app.routes import (
    auth,
    banking,
    cards,
    goals,
    gpt,
    user,
    scores,
    mh_categories,
    voice_therapist,
    mentor_messages,
    father_analysis_cards,
    wellness,
    ai_suggestions,
)
from app.routes.biometrics.fitbit import fitbit_external, fitbit_internal
from app.routes.calendar.google import (
    google_calendar_external,
    google_calendar_internal,
)
from app.admin import setup_admin


# Custom middleware to handle Cloud Run static asset serving
class CloudRunMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Process the request directly
        response = await call_next(request)

        # Only set basic cache headers for static files
        if "/statics/" in request.url.path:
            response.headers["Cache-Control"] = "public, max-age=3600"
            print(f"Static file request: {request.url.path}, response: {response.status_code}")

        return response


middleware = [Middleware(RawContextMiddleware), Middleware(CloudRunMiddleware)]


app = FastAPI(middleware=middleware)


# Add exception handlers for better debugging
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    # Just log the exception for debugging
    print(f"HTTP Exception for {request.url.path}: {exc.status_code} - {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Initialize admin panel
setup_admin(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def startup_event():
    pass
    # Establish connection with DB


@app.get("/")
def get_health():
    return {"message": "Welcome to Con-join-ai!"}


app.add_event_handler("startup", startup_event)

app.include_router(auth.router)
app.include_router(banking.router)
app.include_router(gpt.router)
app.include_router(google_calendar_external.router)
app.include_router(google_calendar_internal.router)
app.include_router(cards.router)
app.include_router(scores.router)
app.include_router(user.router)
app.include_router(goals.router)
app.include_router(fitbit_external.router)
app.include_router(fitbit_internal.router)
app.include_router(mh_categories.router)
app.include_router(voice_therapist.router)
app.include_router(mentor_messages.router)
app.include_router(father_analysis_cards.router)
app.include_router(wellness.router)
app.include_router(ai_suggestions.router)
