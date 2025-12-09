import logging
from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import config
from keyboards.inline_keyboards import get_user_start_keyboard, get_admin_start_keyboard
from database.status_handler import save_user_start_message, get_user_start_message, get_bot_status
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
    
    is_online = get_bot_status()
    status_emoji = "✅" if is_online else "❌"
    status_text = "مُتصل وجاهز للعمل" if is_online else "مُتوقف للصيانة"

    if user_id in config.ADMIN_IDS:
        text = (
            "👑 **لوحة تحكم المشرف (Admin Panel)**\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"🤖 **حالة البوت:** {status_emoji} *{status_text}*\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "مرحباً بك أيها المشرف، يمكنك إدارة حالة البوت والتحكم في عمليات الفحص والإذاعة من هنا."
        )
        keyboard = get_admin_start_keyboard()
    else:
        text = (
            f"👋 **أهلاً بك يا {message.from_user.full_name}!**\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"🤖 **حالة البوت:** {status_emoji} *{status_text}*\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "نحن هنا لخدمتك. يمكنك استخدام الأزرار أدناه للبدء في فحص الحسابات أو فتح واجهة الويب الخاصة بنا.\n\n"
            "*ملاحظة: البوت يعمل بكفاءة عالية لضمان أفضل النتائج.*"
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
    await callback.answer("يتم تحديث الحالة...", show_alert=False)
    
    is_online = get_bot_status()
    status_emoji = "✅" if is_online else "❌"
    status_text = "مُتصل وجاهز للعمل" if is_online else "مُتوقف للصيانة"

    if callback.from_user.id in config.ADMIN_IDS:
        text = (
            "👑 **لوحة تحكم المشرف (Admin Panel)**\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"🤖 **حالة البوت:** {status_emoji} *{status_text}*\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "مرحباً بك أيها المشرف، يمكنك إدارة حالة البوت والتحكم في عمليات الفحص والإذاعة من هنا."
        )
        keyboard = get_admin_start_keyboard()
    else:
        text = (
            f"👋 **أهلاً بك يا {callback.from_user.full_name}!**\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"🤖 **حالة البوت:** {status_emoji} *{status_text}*\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "نحن هنا لخدمتك. يمكنك استخدام الأزرار أدناه للبدء في فحص الحسابات أو فتح واجهة الويب الخاصة بنا.\n\n"
            "*ملاحظة: البوت يعمل بكفاءة عالية لضمان أفضل النتائج.*"
        )
        keyboard = get_user_start_keyboard()
        
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except TelegramBadRequest:
        pass
