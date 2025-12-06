from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.status_handler import get_bot_status

def get_user_start_keyboard() -> InlineKeyboardMarkup:
    is_online = get_bot_status()
    status_text = "ONLINE ✅" if is_online else "OFFLINE ❌"
    status_button = InlineKeyboardButton(text=f"Bot Status: {status_text}", callback_data="check_status")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[status_button]])
    return keyboard

def get_admin_start_keyboard() -> InlineKeyboardMarkup:
    is_online = get_bot_status()
    status_text = "ONLINE ✅" if is_online else "OFFLINE ❌"
    status_button = InlineKeyboardButton(text=f"Bot Status: {status_text}", callback_data="check_status")
    toggle_button_text = "Set to OFFLINE" if is_online else "Set to ONLINE"
    toggle_status_button = InlineKeyboardButton(text=toggle_button_text, callback_data="toggle_status")
    broadcast_button = InlineKeyboardButton(text="📢 Broadcast", callback_data="broadcast")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [status_button],
        [toggle_status_button],
        [broadcast_button]
    ])
    return keyboard
