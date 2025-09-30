import os
import secrets

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2024-10-01")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FITBIT_CLIENT_ID = os.getenv("FITBIT_CLIENT_ID")
FITBIT_CLIENT_SECRET = os.getenv("FITBIT_CLIENT_SECRET")
FITBIT_REDIRECT_URI = os.getenv("FITBIT_REDIRECT_URI")
CODE_VERIFIER = secrets.token_urlsafe(128)[0:128]
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")  # default postgres port is 5432
POSTGRES_DB = os.getenv("POSTGRES_DB")
DATABASE_URL = f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Voice Therapy - OpenAI Realtime API Configuration
REALTIME_VAD_THRESHOLD = float(os.getenv("REALTIME_VAD_THRESHOLD", "0.35"))  # Lower threshold for better voice detection
REALTIME_VAD_PREFIX_PADDING_MS = int(os.getenv("REALTIME_VAD_PREFIX_PADDING_MS", "1000"))  # More padding to avoid cutting off user
REALTIME_VAD_SILENCE_DURATION_MS = int(os.getenv("REALTIME_VAD_SILENCE_DURATION_MS", "2000"))  # Longer silence to let user finish
REALTIME_STT_MODEL = os.getenv("REALTIME_STT_MODEL", "gpt-4o-mini-transcribe")
REALTIME_STT_LANGUAGE = os.getenv("REALTIME_STT_LANGUAGE", "en")


# # Load credentials from JSON
# creds_json = {
#     "web": {
#         "client_id": "66830077574-unqnlois5ph0g4jgv5drhhe6c0q9a5q7.apps.googleusercontent.com",
#         "project_id": "con-join-ai",
#         "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#         "token_uri": "https://oauth2.googleapis.com/token",
#         "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
#         "client_secret": "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"
#     }
# }
