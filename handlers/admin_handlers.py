import asyncio
import logging
from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Filter

import config
from keyboards.inline_keyboards import get_admin_start_keyboard
from database.status_handler import set_bot_status, get_bot_status, get_all_user_message_ids

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
    
    await callback.answer(f"تم تعيين الحالة إلى {'مُتصل' if new_status else 'مُتوقف'}", show_alert=True)
    
    await callback.message.edit_reply_markup(reply_markup=get_admin_start_keyboard())
    
    asyncio.create_task(update_all_users(bot))

async def update_all_users(bot: Bot):
    from keyboards.inline_keyboards import get_user_start_keyboard, get_admin_start_keyboard
    from database.status_handler import get_bot_status
    
    all_users = get_all_user_message_ids()
    if not all_users:
        return

    logger.info(f"Starting status update for {len(all_users)} users.")
    
    is_online = get_bot_status()
    status_emoji = "✅" if is_online else "❌"
    status_text = "مُتصل وجاهز للعمل" if is_online else "مُتوقف للصيانة"

    for user_id_str, data in all_users.items():
        user_id = int(user_id_str)
        message_id = data.get('start_message_id')
        
        if not message_id:
            continue
        
        if user_id in config.ADMIN_IDS:
            keyboard = get_admin_start_keyboard()
            text = (
                "👑 **لوحة تحكم المشرف (Admin Panel)**\n"
                "➖➖➖➖➖➖➖➖➖➖➖➖\n"
                f"🤖 **حالة البوت:** {status_emoji} *{status_text}*\n"
                "➖➖➖➖➖➖➖➖➖➖➖➖\n"
                "مرحباً بك أيها المشرف، يمكنك إدارة حالة البوت والتحكم في عمليات الفحص والإذاعة من هنا."
            )
        else:
            keyboard = get_user_start_keyboard()
            text = (
                f"👋 **أهلاً بك!**\n"
                "➖➖➖➖➖➖➖➖➖➖➖➖\n"
                f"🤖 **حالة البوت:** {status_emoji} *{status_text}*\n"
                "➖➖➖➖➖➖➖➖➖➖➖➖\n"
                "نحن هنا لخدمتك. يمكنك استخدام الأزرار أدناه للبدء في فحص الحسابات أو فتح واجهة الويب الخاصة بنا.\n\n"
                "*ملاحظة: البوت يعمل بكفاءة عالية لضمان أفضل النتائج.*"
            )
        
        try:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"Could not update user {user_id}: {e}")
            continue
    logger.info("Finished updating all users.")

@router.callback_query(F.data == "broadcast", IsAdmin())
async def start_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("الرجاء إرسال الرسالة التي تود بثها لجميع المستخدمين. يمكنك استخدام تنسيق Markdown.")
    await state.set_state(BroadcastState.awaiting_message)
    await callback.answer()

@router.message(BroadcastState.awaiting_message, IsAdminMessage())
async def process_broadcast_message(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    
    all_users = get_all_user_message_ids()
    if not all_users:
        await message.answer("⚠️ لا يوجد مستخدمون مسجلون في قاعدة البيانات لإرسال الإذاعة إليهم.")
        return
        
    await message.answer(f"بدء عملية البث لـ {len(all_users)} مستخدم...")
    
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
            
    await message.answer(f"📢 اكتمل البث!\n\n✅ تم الإرسال إلى: {success_count} مستخدم\n❌ فشل الإرسال إلى: {fail_count} مستخدم")
