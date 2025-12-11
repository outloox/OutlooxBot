import firebase_admin
from firebase_admin import credentials, db
import json
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    # Read the JSON content from the environment variable
    creds_json_str = os.environ.get("FIREBASE_CREDS_JSON")
    if creds_json_str:
        # Use the JSON string directly to create credentials
        cred = credentials.Certificate(json.loads(creds_json_str))
        firebase_admin.initialize_app(cred, {'databaseURL': os.environ.get("FIREBASE_DB_URL")})
        logger.info("Firebase Admin SDK initialized successfully from environment variable.")
    else:
        # Fallback to file path if environment variable is not set (for local testing)
        cred = credentials.Certificate("/firebase-credentials.json")
        firebase_admin.initialize_app(cred, {'databaseURL': os.environ.get("FIREBASE_DB_URL")})
        logger.info("Firebase Admin SDK initialized successfully from file path.")
except Exception as e:
    logger.critical(f"Failed to initialize Firebase Admin SDK: {e}")

def get_status_ref():
    return db.reference('bot_status')

def get_users_ref():
    return db.reference('users')

def get_bot_status() -> bool:
    ref = get_status_ref()
    status = ref.child('online').get()
    return status if status is not None else True

def set_bot_status(status: bool):
    ref = get_status_ref()
    ref.update({'online': status})

def save_user_start_message(user_id: int, message_id: int):
    ref = get_users_ref()
    # Ensure user is registered in the database for broadcast
    ref.child(str(user_id)).update({'start_message_id': message_id, 'is_registered': True})

def get_user_start_message(user_id: int) -> int:
    ref = get_users_ref()
    data = ref.child(str(user_id)).get()
    return data.get('start_message_id') if data else None

def get_all_user_message_ids() -> dict:
    ref = get_users_ref()
    # Filter only registered users for broadcast
    users_data = ref.order_by_child('is_registered').equal_to(True).get()
    return users_data if users_data else {}
