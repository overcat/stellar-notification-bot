import asyncio

from loguru import logger
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import Forbidden

from src.config import tg_app
from src.db import Message, Chat


async def send_telegram_message(message: Message):
    try:
        await tg_app.bot.send_message(
            chat_id=message.chat_id,
            text=message.content,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="View on stellar.expert",
                            url=f"https://stellar.expert/explorer/public/tx/{message.tx_hash}",
                        )
                    ],
                ]
            ),
        )
        await message.remove()
    except Forbidden as e:
        logger.debug(f"Message {message.id} not sent: {e}")
        await Chat.disable_notification(message.chat_id)


async def send_notification():
    while True:
        message = await Message.get_oldest_unsent_message()
        if message is None:
            logger.debug("No unsent message found.")
            await asyncio.sleep(3)
            continue
        # If you're sending bulk notifications to multiple users,
        # the API will not allow more than 30 messages per second or so
        # https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this
        # But we don't need to worry about this because low traffic.
        await send_telegram_message(message)
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    logger.info("Starting send notification...")
    asyncio.run(send_notification())
