import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.middleware.base import BaseHTTPMiddleware
from wtforms import SelectField

from app.postgres.database import engine
from app.postgres.schema.card import (
    CardCompletionDetail,
    CardDetail,
    CardStatus,
    CardType,
    CategoryEnum,
    CompletionLevel,
    HowWasIt,
    SpecialActions,
    TimeOfDay,
    UserCard,
)
from app.postgres.schema.cognitive_fingerprint import CognitiveFingerprint
from app.postgres.schema.cognitive_score import CognitiveScore
from app.postgres.schema.external_token import ExternalToken
from app.postgres.schema.fitbit_heart import (
    FitbitHeartLog,
)
from app.postgres.schema.fitbit_sleep import (
    FitbitSleepLog,
)
from app.postgres.schema.goals import Goal, UserGoals
from app.postgres.schema.google_calendar import (
    CalendarEvent,
)

# Import your SQLAlchemy models
from app.postgres.schema.user import User
from app.postgres.schema.user_preferences import UserPreferences

# Load environment variables
load_dotenv()


# Create an authentication backend
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # Get admin credentials from environment variables or use defaults
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "conjoinadmin123")

        # Validate the username and password
        if username == admin_username and password == admin_password:
            request.session.update({"token": "admin"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if token == "admin":
            return True
        return False


# Create middleware to fix HTTP/HTTPS mixed content issues
class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Add Content-Security-Policy to allow loading resources over HTTPS
        response.headers["Content-Security-Policy"] = "upgrade-insecure-requests"
        return response


def setup_admin(app: FastAPI):
    # Add middleware to handle mixed content
    app.add_middleware(SecureHeadersMiddleware)

    # Import sqladmin module to get its path
    import sqladmin

    # Get the path to sqladmin's statics directory
    sqladmin_path = os.path.dirname(sqladmin.__file__)
    static_directory = os.path.join(sqladmin_path, "statics")

    print(f"Using sqladmin static files from: {static_directory}")
    print(f"Current directory: {os.getcwd()}")

    # Make this extremely verbose for debugging
    print(f"Static directory exists: {os.path.exists(static_directory)}")
    if os.path.exists(static_directory):
        print(f"Static directory contents: {os.listdir(static_directory)}")

    # Mount static files explicitly with name
    app.mount("/admin/statics", StaticFiles(directory=static_directory), name="admin_statics")

    # Create authentication backend
    authentication_backend = AdminAuth(secret_key=os.getenv("SECRET_KEY"))

    # Initialize Admin with authentication
    admin = Admin(app, engine, authentication_backend=authentication_backend, title="Conjoin Admin", base_url="/admin")

    # Register each model with the admin interface
    class UserAdmin(ModelView, model=User):
        column_list = [User.user_id, User.email, User.firstname, User.surname, User.created_at]
        name = "User"
        icon = "fa-solid fa-user"

        # Add labels to indicate which fields are optional
        column_labels = {
            "home": "Home (optional)",
            "office": "Office (optional)",
            "completed_morning_orientation": "Completed Morning Orientation (optional)",
            "completed_morning_orientation_date": "Completed Morning Orientation Date (optional)",
        }

    class UserCardAdmin(ModelView, model=UserCard):
        column_list = [UserCard.card_id, UserCard.user_id, UserCard.time, UserCard.created_at]
        name = "User Card"
        icon = "fa-solid fa-id-card"

        # Add labels to indicate which fields are optional
        column_labels = {
            "recurrence": "Recurrence (optional)",
            "calendar_event_id": "Calendar Event ID (optional)",
            "location": "Location (optional)",
        }

    class CardDetailAdmin(ModelView, model=CardDetail):
        column_list = [CardDetail.id, CardDetail.title, CardDetail.card_type, CardDetail.category]
        name = "Card Detail"
        icon = "fa-solid fa-info-circle"

        # Add labels to indicate which fields are optional
        column_labels = {
            "category": "Category (optional)",
            "description": "Description (optional)",
            "tod": "Time of Day (optional)",
            "special_card_action": "Special Card Action (optional)",
            "affirmation_number": "Affirmation Number (optional)",
        }

        # Specify the choices for each enum field
        form_overrides = {
            "card_type": SelectField,
            "category": SelectField,
            "tod": SelectField,
            "special_card_action": SelectField,
        }

        form_args = {
            "card_type": {
                "choices": [(t.name, t.name) for t in CardType],
            },
            "category": {
                "choices": [(c.name, c.name) for c in CategoryEnum],
            },
            "tod": {
                "choices": [(t.name, t.name) for t in TimeOfDay],
            },
            "special_card_action": {
                "choices": [(a.name, a.name) for a in SpecialActions] + [("", "None")],
            },
        }

    class CardCompletionDetailAdmin(ModelView, model=CardCompletionDetail):
        column_list = [CardCompletionDetail.id, CardCompletionDetail.card_id, CardCompletionDetail.status, CardCompletionDetail.completion_level]
        name = "Card Completion Detail"
        icon = "fa-solid fa-check-circle"

        # Override the form fields for enum types to use dropdowns
        form_overrides = {
            "status": SelectField,
            "completion_level": SelectField,
            "how_was_it": SelectField,
        }

        # Specify the choices for each enum field
        form_args = {
            "status": {
                "choices": [(s.name, s.name) for s in CardStatus],
            },
            "completion_level": {
                "choices": [(c.name, c.name) for c in CompletionLevel],
            },
            "how_was_it": {
                "choices": [(h.name, h.name) for h in HowWasIt],
            },
        }

    class ExternalTokenAdmin(ModelView, model=ExternalToken):
        column_list = [ExternalToken.id, ExternalToken.user_id, ExternalToken.service_name]
        name = "External Token"
        icon = "fa-solid fa-key"

        # Add labels to indicate which fields are optional
        column_labels = {"expires_at": "Expires At (optional)"}

    class GoalAdmin(ModelView, model=Goal):
        column_list = [Goal.id, Goal.name]
        name = "Goal"
        icon = "fa-solid fa-bullseye"

    class UserGoalsAdmin(ModelView, model=UserGoals):
        column_list = [UserGoals.id, UserGoals.user_id, UserGoals.goal_id, UserGoals.target, UserGoals.completed]
        name = "User Goal"
        icon = "fa-solid fa-tasks"

        # Add labels to indicate which fields are optional
        column_labels = {"target": "Target (optional)", "completed": "Completed (optional)"}

    class CognitiveScoreAdmin(ModelView, model=CognitiveScore):
        column_list = [CognitiveScore.id, CognitiveScore.user_id, CognitiveScore.score]
        name = "Cognitive Score"
        icon = "fa-solid fa-chart-line"

        # Add labels to indicate which fields are optional
        column_labels = {"score": "Score (optional)"}

    class FitbitSleepAdmin(ModelView, model=FitbitSleepLog):
        column_list = [FitbitSleepLog.log_id, FitbitSleepLog.user_id, FitbitSleepLog.date_of_sleep, FitbitSleepLog.duration]
        name = "Fitbit Sleep Log"
        icon = "fa-solid fa-bed"

        # Add labels to indicate which fields are optional
        column_labels = {
            "efficiency": "Efficiency (optional)",
            "end_time": "End Time (optional)",
            "info_code": "Info Code (optional)",
            "is_main_sleep": "Is Main Sleep (optional)",
            "minutes_after_wakeup": "Minutes After Wakeup (optional)",
            "minutes_asleep": "Minutes Asleep (optional)",
            "minutes_awake": "Minutes Awake (optional)",
            "minutes_to_fall_asleep": "Minutes To Fall Asleep (optional)",
            "start_time": "Start Time (optional)",
            "time_in_bed": "Time In Bed (optional)",
            "log_type": "Log Type (optional)",
            "sleep_type": "Sleep Type (optional)",
        }

    class FitbitHeartAdmin(ModelView, model=FitbitHeartLog):
        column_list = [FitbitHeartLog.log_id, FitbitHeartLog.user_id, FitbitHeartLog.date_time, FitbitHeartLog.resting_heart_rate]
        name = "Fitbit Heart Log"
        icon = "fa-solid fa-heartbeat"

        # Add labels to indicate which fields are optional
        column_labels = {"resting_heart_rate": "Resting Heart Rate (optional)"}

    class CalendarEventAdmin(ModelView, model=CalendarEvent):
        column_list = [CalendarEvent.id, CalendarEvent.user_id, CalendarEvent.summary, CalendarEvent.created]
        name = "Calendar Event"
        icon = "fa-solid fa-calendar"

        # Add labels to indicate which fields are optional
        column_labels = {
            "status": "Status (optional)",
            "htmlLink": "HTML Link (optional)",
            "created": "Created (optional)",
            "updated": "Updated (optional)",
            "summary": "Summary (optional)",
            "description": "Description (optional)",
            "location": "Location (optional)",
            "colorId": "Color ID (optional)",
            "endTimeUnspecified": "End Time Unspecified (optional)",
            "recurrence": "Recurrence (optional)",
            "recurringEventId": "Recurring Event ID (optional)",
            "transparency": "Transparency (optional)",
            "visibility": "Visibility (optional)",
            "iCalUID": "iCal UID (optional)",
            "sequence": "Sequence (optional)",
            "hangoutLink": "Hangout Link (optional)",
            "anyoneCanAddSelf": "Anyone Can Add Self (optional)",
            "guestsCanInviteOthers": "Guests Can Invite Others (optional)",
            "guestsCanModify": "Guests Can Modify (optional)",
            "guestsCanSeeOtherGuests": "Guests Can See Other Guests (optional)",
            "privateCopy": "Private Copy (optional)",
            "locked": "Locked (optional)",
            "source_url": "Source URL (optional)",
            "source_title": "Source Title (optional)",
            "eventType": "Event Type (optional)",
            "creator_id": "Creator ID (optional)",
            "organizer_id": "Organizer ID (optional)",
            "start_id": "Start ID (optional)",
            "end_id": "End ID (optional)",
        }

    class UserPreferencesAdmin(ModelView, model=UserPreferences):
        column_list = [UserPreferences.id, UserPreferences.user_id, UserPreferences.preferenceName, UserPreferences.category]
        name = "User Preference"
        icon = "fa-solid fa-sliders-h"

        # Add labels to indicate which fields are optional
        column_labels = {"preferenceMetric": "Preference Metric (optional)"}

        # Override the form fields for enum types to use dropdowns
        form_overrides = {
            "category": SelectField,
        }

        # Specify the choices for each enum field
        form_args = {
            "category": {
                "choices": [(c.name, c.name) for c in CategoryEnum],
            },
        }

    class CognitiveFingerprintAdmin(ModelView, model=CognitiveFingerprint):
        column_list = [CognitiveFingerprint.fingerprint_id, CognitiveFingerprint.user_id, CognitiveFingerprint.created_at]
        name = "Cognitive Fingerprint"
        icon = "fa-solid fa-fingerprint"

    # Add all model views to the admin interface
    admin.add_view(UserAdmin)
    admin.add_view(UserCardAdmin)
    admin.add_view(CardDetailAdmin)
    admin.add_view(CardCompletionDetailAdmin)
    admin.add_view(GoalAdmin)
    admin.add_view(UserGoalsAdmin)
    admin.add_view(CognitiveScoreAdmin)
    # admin.add_view(FitbitSleepAdmin)
    # admin.add_view(FitbitHeartAdmin)
    # admin.add_view(CalendarEventAdmin)
    # admin.add_view(UserPreferencesAdmin)
    admin.add_view(CognitiveFingerprintAdmin)

    return admin
