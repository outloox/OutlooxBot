import logging
from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import config
from keyboards.inline_keyboards import get_user_start_keyboard, get_admin_start_keyboard
from database.status_handler import save_user_start_message, get_user_start_message
from utils.message_utils import send_or_edit_message

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def handle_start(message: types.Message, bot: Bot, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    existing_message_id = get_user_start_message(user_id)

    if user_id in config.ADMIN_IDS:
        text = "👑 **Welcome, Admin!**\n\nThis is your control panel. You can manage the bot's status and communicate with users."
        keyboard = get_admin_start_keyboard()
    else:
        text = (
            "👋 **Welcome to the Account Checker Bot!**\n\n"
            "I am here to assist you. You can check the bot's operational status below.\n\n"
            "*Please note: This bot is for demonstration purposes.*"
        )
        keyboard = get_user_start_keyboard()

    sent_message = await send_or_edit_message(
        bot=bot,
        chat_id=user_id,
        text=text,
        keyboard=keyboard,
        message_id=existing_message_id
    )
    
    if sent_message:
        save_user_start_message(user_id, sent_message.message_id)

@router.callback_query(F.data == "check_status")
async def handle_status_check(callback: types.CallbackQuery):
    await callback.answer("Refreshing status...", show_alert=False)
    
    keyboard = get_user_start_keyboard() if callback.from_user.id not in config.ADMIN_IDS else get_admin_start_keyboard()
    
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except TelegramBadRequest:
        pass
