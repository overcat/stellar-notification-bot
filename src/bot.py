from stellar_sdk import Keypair
from stellar_sdk.exceptions import Ed25519PublicKeyInvalidError
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from src.config import tg_app
from src.db import Chat


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    Chat.new_chat(chat_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Hello, I'm Stellar Notification Bot! "
        "Please add your Stellar account by /add command.",
    )


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    account_id = context.args[0].strip()
    try:
        Keypair.from_public_key(account_id)
        Chat.add_stellar_account(chat_id, account_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Added successfully! You will receive notifications "
            f"when the account's balance changes.",
            reply_to_message_id=update.message.message_id,
        )
    except Ed25519PublicKeyInvalidError:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Invalid account id: `{account_id}`",
            reply_to_message_id=update.message.message_id,
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    account_id = context.args[0].strip()
    Chat.remove_stellar_account(chat_id, account_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Removed successfully! You will not receive notifications "
        f"when the account's balance changes.",
        reply_to_message_id=update.message.message_id,
    )


tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("add", add))
tg_app.add_handler(CommandHandler("remove", remove))

if __name__ == "__main__":
    tg_app.run_polling()