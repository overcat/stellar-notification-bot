import asyncio
import time

from loguru import logger
from telegram.constants import ParseMode
from telegram.error import Forbidden

from src.config import tg_app
from src.db import Message, Chat


def send_telegram_message(message: Message):
    try:
        asyncio.run(
            tg_app.bot.send_message(
                chat_id=message.chat_id,
                text=message.content,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        )
        message.remove()
    except Forbidden as e:
        logger.debug(f"Message {message.id} not sent: {e}")
        Chat.disable_notification(message.chat_id)


def send_notification():
    while True:
        message = Message.get_oldest_unsent_message()
        if message is None:
            logger.info("No unsent message found.")
            time.sleep(1)
            continue
        # If you're sending bulk notifications to multiple users,
        # the API will not allow more than 30 messages per second or so
        # https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this
        # But we don't need to worry about this because low traffic.
        send_telegram_message(message)
        time.sleep(0.5)


if __name__ == "__main__":
    send_notification()
