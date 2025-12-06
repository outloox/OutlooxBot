from .firebase_handler import db_ref

def set_bot_status(is_online: bool):
    if not db_ref: return
    status_ref = db_ref.child('bot_status')
    status_ref.set({'is_online': is_online})

def get_bot_status() -> bool:
    if not db_ref: return True
    status = db_ref.child('bot_status/is_online').get()
    return status if isinstance(status, bool) else True

def save_user_start_message(user_id: int, message_id: int):
    if not db_ref: return
    user_ref = db_ref.child(f'user_messages/{user_id}')
    user_ref.set({'start_message_id': message_id})

def get_all_user_message_ids() -> dict:
    if not db_ref: return {}
    messages = db_ref.child('user_messages').get()
    return messages or {}

def get_user_start_message(user_id: int) -> int | None:
    if not db_ref: return None
    message_id = db_ref.child(f'user_messages/{user_id}/start_message_id').get()
    return message_id
