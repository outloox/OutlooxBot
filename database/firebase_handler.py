import logging
from firebase_admin import credentials, db, initialize_app, get_app
from config import FIREBASE_DB_URL

logger = logging.getLogger(__name__)
db_ref = None

def initialize_firebase():
    global db_ref
    try:
        cred = credentials.Certificate("firebase-credentials.json")
        logger.info("Initializing Firebase from virtual file.")

        try:
            get_app()
        except ValueError:
            initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
        
        db_ref = db.reference()
        logger.info("Firebase Admin SDK initialized successfully.")
        return db_ref
    except Exception as e:
        logger.critical(f"Failed to initialize Firebase Admin SDK: {e}")
        return None
