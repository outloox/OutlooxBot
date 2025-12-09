import logging
import re
from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

import config
from keyboards.inline_keyboards import get_user_start_keyboard, get_admin_start_keyboard
from database.status_handler import save_user_start_message, get_user_start_message, get_bot_status
from utils.message_utils import send_or_edit_message
from utils.account_checker import check_account, upload_to_firebase, format_result_message

router = Router()
logger = logging.getLogger(__name__)

class AccountCheckStates(StatesGroup):
    awaiting_accounts = State()
    
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

@router.callback_query(F.data.in_({"check_accounts_no_save", "check_accounts_save"}))
async def start_account_check(callback: types.CallbackQuery, state: FSMContext):
    if not get_bot_status():
        await callback.answer("⚠️ البوت مُتوقف حالياً للصيانة. الرجاء المحاولة لاحقاً.", show_alert=True)
        return

    save_to_db = callback.data == "check_accounts_save"
    
    await state.update_data(save_to_db=save_to_db)
    
    action_text = "وحفظها في قاعدة البيانات" if save_to_db else "دون حفظها"
    
    await callback.message.answer(
        f"✅ **وضع الفحص مُفعل!**\n\n"
        f"الرجاء إرسال الحسابات الآن بالتنسيق التالي (بريد:كلمة مرور)، يمكن إرسال عدة حسابات في رسالة واحدة.\n\n"
        f"سيتم فحص الحسابات {action_text}."
    )
    await state.set_state(AccountCheckStates.awaiting_accounts)
    await callback.answer()

@router.message(AccountCheckStates.awaiting_accounts)
async def process_accounts(message: types.Message, state: FSMContext):
    data = await state.get_data()
    save_to_db = data.get("save_to_db", False)
    
    accounts = re.findall(r'([\w\.-]+@[\w\.-]+\.[\w\.-]+):(.+)', message.text)
    
    if not accounts:
        await message.reply("❌ **تنسيق خاطئ!**\n\nالرجاء إرسال الحسابات بالتنسيق الصحيح: `بريد:كلمة مرور`.")
        return

    await state.clear()
    
    status_msg = await message.reply(f"⏳ **بدء الفحص لـ {len(accounts)} حساب...**")
    
    tasks = []
    for email, password in accounts:
        tasks.append(asyncio.create_task(process_single_account(email, password, save_to_db, status_msg.chat.id, status_msg.message_id)))
        
    await asyncio.gather(*tasks)
    
    await status_msg.edit_text("✅ **اكتمل الفحص!**\n\nتم إرسال النتائج في رسائل منفصلة.", reply_markup=None)

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
            f"❌ **فشل فحص الحساب**\n\n"
            f"📧 **البريد:** `{email}`\n"
            f"🔑 **كلمة المرور:** `{password}`\n"
            f"🛑 **السبب:** {error}",
            parse_mode="Markdown"
        )
