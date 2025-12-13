import logging
import re
from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup
from aiogram.exceptions import TelegramBadRequest

import config
from keyboards.inline_keyboards import get_user_start_keyboard, get_admin_start_keyboard, get_back_to_menu_keyboard
from database.status_handler import save_user_start_message, get_user_start_message, get_bot_status
from utils.message_utils import send_or_edit_message
from utils.account_checker import check_account, upload_to_firebase, format_result_message
import asyncio

router = Router()
logger = logging.getLogger(__name__)

class AccountCheckStates(StatesGroup):
    awaiting_accounts = State()
    
def get_start_message_text(user_id: int, full_name: str) -> str:
    is_online = get_bot_status()
    status_emoji = "✅" if is_online else "❌"
    status_text = "Online & Ready" if is_online else "Offline for Maintenance"
    
    if user_id in config.ADMIN_IDS:
        text = (
            "👑 **Admin Control Panel**\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"🤖 **Bot Status:** {status_emoji} *{status_text}*\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "Welcome, Admin. Manage bot status, checking operations, and broadcasting from here.\n\nType /start to return to this menu."
        )
    else:
        text = (
            f"👋 **Hello, {full_name}!**\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"🤖 **Bot Status:** {status_emoji} *{status_text}*\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "Use the buttons below to start checking accounts or access our WebApp.\n\nType /start to return to this menu."
            "*Note: The bot is designed for high-efficiency account checking.*"
        )
    return text

@router.message(CommandStart())
async def handle_start(message: types.Message, bot: Bot, state: FSMContext):
    try:
        await state.clear()
    except Exception:
        pass
    user_id = message.from_user.id
    
    # User's /start message is kept

    existing_message_id = get_user_start_message(user_id)
    
    text = get_start_message_text(user_id, message.from_user.full_name)
    keyboard = get_admin_start_keyboard() if user_id in config.ADMIN_IDS else get_user_start_keyboard()

    sent_message = await send_or_edit_message(
        bot=bot,
        chat_id=user_id,
        text=text,
        keyboard=keyboard,
        message_id=existing_message_id
    )
    
    if sent_message:
        save_user_start_message(user_id, sent_message.message_id)

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    try:
        await state.clear()
    except Exception:
        pass
    user_id = callback.from_user.id
    
    text = get_start_message_text(user_id, callback.from_user.full_name)
    keyboard = get_admin_start_keyboard() if user_id in config.ADMIN_IDS else get_user_start_keyboard()
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise e
    await callback.answer()

@router.callback_query(F.data == "check_status")
async def handle_status_check(callback: types.CallbackQuery):
    await callback.answer("Refreshing status...", show_alert=False)
    
    user_id = callback.from_user.id
    text = get_start_message_text(user_id, callback.from_user.full_name)
    keyboard = get_admin_start_keyboard() if user_id in config.ADMIN_IDS else get_user_start_keyboard()
        
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise e

@router.callback_query(F.data.in_({"check_accounts_no_save", "check_accounts_save"}))
async def start_account_check(callback: types.CallbackQuery, state: FSMContext):
    if not get_bot_status():
        await callback.answer("⚠️ Bot is currently offline for maintenance.", show_alert=True)
        return

    save_to_db = callback.data == "check_accounts_save"
    
    await state.update_data(save_to_db=save_to_db)
    
    action_text = "and save to database" if save_to_db else "without saving"
    
    await callback.message.edit_text(
        f"✅ **Check Mode Activated!**\n\n"
        f"Please send accounts now in the format (email:password). Multiple accounts can be sent in one message.\n\n"
        f"Accounts will be checked {action_text}.",
        reply_markup=get_back_to_menu_keyboard()
    )
    await state.set_state(AccountCheckStates.awaiting_accounts)
    await callback.answer()

@router.message(AccountCheckStates.awaiting_accounts)
async def process_accounts(message: types.Message, bot: Bot, state: FSMContext):
    data = await state.get_data()
    save_to_db = data.get("save_to_db", False)
    
    accounts = re.findall(r'([\w\.-]+@[\w\.-]+\.[\w\.-]+):(.+)', message.text)
    
    # User's message is kept
    
    if not accounts:
        await message.reply("❌ **Invalid Format!**\n\nPlease send accounts in the correct format: `email:password`.", reply_markup=get_back_to_menu_keyboard())
        return

    try:
        await state.clear()
    except Exception:
        pass
    
    status_msg = await message.reply(f"⏳ **Starting check for {len(accounts)} accounts...**")
    
    tasks = []
    for email, password in accounts:
        tasks.append(asyncio.create_task(process_single_account(email, password, save_to_db, status_msg.chat.id, status_msg.message_id)))
        
    await asyncio.gather(*tasks)
    
    await status_msg.edit_text("✅ **Check Complete!**\n\nResults have been sent in separate messages.", reply_markup=get_back_to_menu_keyboard())

async def process_single_account(email: str, password: str, save_to_db: bool, chat_id: int, status_message_id: int):
    details, error = await check_account(email, password)
    
    if details:
        details['email'] = email
        details['password'] = password
        
        if save_to_db:
            await upload_to_firebase(details)
            
        result_text = format_result_message(details, save_to_db)
        
        await Bot.get_current().send_message(chat_id, result_text, parse_mode="Markdown")
    else:
        await Bot.get_current().send_message(
            chat_id,
            f"❌ **Account Check Failed**\n\n"
            f"📧 **Email:** `{email}`\n"
            f"🔑 **Password:** `{password}`\n"
            f"🛑 **Reason:** {error}",
            parse_mode="Markdown"
        )
