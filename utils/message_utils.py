from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

async def send_or_edit_message(
    bot: Bot,
    chat_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup = None,
    message_id: int = None
) -> Message:
    try:
        if message_id:
            edited_message = await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            return edited_message
    except TelegramBadRequest as e:
        if "message to edit not found" in e.message or "message is not modified" in e.message:
            pass
        else:
            raise e

    new_message = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return new_message
