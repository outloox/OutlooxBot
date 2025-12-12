from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
import re

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
        if "message is not modified" in e.message:
            # Ignore this error as it's not critical
            pass
        elif "message to edit not found" in e.message or "message can't be edited" in e.message:
            # If the message ID is invalid (e.g., user deleted it), send a new one
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

def escape_markdown(text: str) -> str:
    """Escapes characters that have special meaning in Telegram Markdown V2."""
    # List of special characters that need to be escaped
    # _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
