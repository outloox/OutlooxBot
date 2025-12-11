from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.status_handler import get_bot_status
from config import WEB_APP_URL

def get_user_start_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡️ Start Check (Save)", callback_data="check_accounts_save")
        ],
        [
            InlineKeyboardButton(text="🌐 Open WebApp", web_app={"url": WEB_APP_URL})
        ]
    ])
    return keyboard

def get_admin_start_keyboard() -> InlineKeyboardMarkup:
    is_online = get_bot_status()
    toggle_button_text = "🔴 Set OFFLINE" if is_online else "🟢 Set ONLINE"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡️ Start Check (Save)", callback_data="check_accounts_save"),
            InlineKeyboardButton(text="🔍 Check (No Save)", callback_data="check_accounts_no_save")
        ],
        [
            InlineKeyboardButton(text="🌐 Open WebApp", web_app={"url": WEB_APP_URL}),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="broadcast")
        ],
        [
            InlineKeyboardButton(text=toggle_button_text, callback_data="toggle_status")
        ]
    ])
    return keyboard

def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_to_menu")
        ]
    ])
    return keyboard
