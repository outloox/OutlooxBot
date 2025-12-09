from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.status_handler import get_bot_status
from config import WEB_APP_URL

def get_user_start_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 فحص الحسابات (بدون حفظ)", callback_data="check_accounts_no_save"),
            InlineKeyboardButton(text="💾 فحص وحفظ في Firebase", callback_data="check_accounts_save")
        ],
        [
            InlineKeyboardButton(text="🌐 فتح واجهة الويب (WebApp)", web_app={"url": WEB_APP_URL})
        ]
    ])
    return keyboard

def get_admin_start_keyboard() -> InlineKeyboardMarkup:
    is_online = get_bot_status()
    toggle_button_text = "🔴 إيقاف البوت (OFFLINE)" if is_online else "🟢 تشغيل البوت (ONLINE)"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 فحص الحسابات (بدون حفظ)", callback_data="check_accounts_no_save"),
            InlineKeyboardButton(text="💾 فحص وحفظ في Firebase", callback_data="check_accounts_save")
        ],
        [
            InlineKeyboardButton(text="🌐 فتح واجهة الويب (WebApp)", web_app={"url": WEB_APP_URL})
        ],
        [
            InlineKeyboardButton(text=toggle_button_text, callback_data="toggle_status"),
            InlineKeyboardButton(text="📢 إرسال إذاعة عامة", callback_data="broadcast")
        ]
    ])
    return keyboard
