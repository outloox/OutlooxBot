import asyncio
import logging
from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Filter

import config
from keyboards.inline_keyboards import get_admin_start_keyboard, get_back_to_menu_keyboard
from database.status_handler import set_bot_status, get_bot_status, get_all_user_message_ids
from handlers.user_handlers import get_start_message_text

router = Router()
logger = logging.getLogger(__name__)

class BroadcastState(StatesGroup):
    awaiting_message = State()

class IsAdmin(Filter):
    async def __call__(self, callback: types.CallbackQuery) -> bool:
        return callback.from_user.id in config.ADMIN_IDS

class IsAdminMessage(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id in config.ADMIN_IDS

@router.callback_query(F.data == "toggle_status", IsAdmin())
async def toggle_bot_status(callback: types.CallbackQuery, bot: Bot):
    current_status = get_bot_status()
    new_status = not current_status
    set_bot_status(new_status)
    
    await callback.answer(f"Status set to {'ONLINE' if new_status else 'OFFLINE'}", show_alert=True)
    
    # Update the admin's own message immediately
    text = get_start_message_text(callback.from_user.id, callback.from_user.full_name)
    keyboard = get_admin_start_keyboard()
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise e
    
    # Update all other users in the background
    asyncio.create_task(update_all_users(bot))

async def update_all_users(bot: Bot):
    from keyboards.inline_keyboards import get_user_start_keyboard
    
    all_users = get_all_user_message_ids()
    if not all_users:
        return

    logger.info(f"Starting status update for {len(all_users)} users.")
    
    for user_id_str, data in all_users.items():
        user_id = int(user_id_str)
        message_id = data.get('start_message_id')
        
        if not message_id or user_id in config.ADMIN_IDS:
            continue
        
        keyboard = get_user_start_keyboard()
        text = get_start_message_text(user_id, "") # Full name is not available here, so we use an empty string
        
        try:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await asyncio.sleep(0.1)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                logger.warning(f"Could not update user {user_id}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Could not update user {user_id}: {e}")
            continue
    logger.info("Finished updating all users.")

@router.callback_query(F.data == "broadcast", IsAdmin())
async def start_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Please send the message you want to broadcast to all users. Markdown is supported.", reply_markup=get_back_to_menu_keyboard())
    await state.set_state(BroadcastState.awaiting_message)
    await callback.answer()

@router.message(BroadcastState.awaiting_message, IsAdminMessage())
async def process_broadcast_message(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    
    # User's message is kept
    
    all_users = get_all_user_message_ids()
    
    if not all_users:
        await message.answer("⚠️ No registered users found to broadcast to.", reply_markup=get_back_to_menu_keyboard())
        return
        
    status_msg = await message.answer(f"Starting broadcast to {len(all_users)} users...")
    
    success_count = 0
    fail_count = 0
    
    for user_id_str in all_users.keys():
        try:
            await bot.copy_message(
                chat_id=int(user_id_str),
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                parse_mode="Markdown"
            )
            success_count += 1
            await asyncio.sleep(0.1)
        except TelegramBadRequest:
            fail_count += 1
            
    await status_msg.edit_text(f"📢 Broadcast Complete!\n\n✅ Sent to: {success_count} users\n❌ Failed for: {fail_count} users", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")
