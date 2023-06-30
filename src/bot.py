import loguru
from stellar_sdk import Keypair, ServerAsync
from stellar_sdk.exceptions import Ed25519PublicKeyInvalidError
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from src.config import tg_app, config
from src.db import Chat, SystemInfo


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    chat_id = update.effective_chat.id
    await Chat.new_chat(chat_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Hello, I'm Stellar Notification Bot! "
        "Please add your Stellar account by /add command.",
    )


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    assert update.message is not None
    chat_id = update.effective_chat.id
    if context.args is None or len(context.args) != 1:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /add <account id>",
            reply_to_message_id=update.message.message_id,
        )
        return
    account_id = context.args[0].strip()
    try:
        Keypair.from_public_key(account_id)
        await Chat.add_stellar_account(chat_id, account_id)
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
    assert update.effective_chat is not None
    assert update.message is not None
    chat_id = update.effective_chat.id
    if context.args is None or len(context.args) != 1:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /remove <account id>",
            reply_to_message_id=update.message.message_id,
        )
        return
    account_id = context.args[0].strip()
    await Chat.remove_stellar_account(chat_id, account_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Removed successfully! You will not receive notifications "
        f"when the account's balance changes.",
        reply_to_message_id=update.message.message_id,
    )


async def enable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    assert update.message is not None
    chat_id = update.effective_chat.id
    await Chat.enable_notification(chat_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Enabled successfully! You will receive notifications "
        f"when the account's balance changes.",
        reply_to_message_id=update.message.message_id,
    )


async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    assert update.message is not None
    chat_id = update.effective_chat.id
    await Chat.disable_notification(chat_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Disabled successfully! You will not receive notifications "
        f"when the account's balance changes.",
        reply_to_message_id=update.message.message_id,
    )


async def system(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    assert update.message is not None
    chat_id = update.effective_chat.id

    latest_processed_ledger = await SystemInfo.get_processed_ledger()

    async with ServerAsync(config.horizon_url) as server:
        latest_ledger = (await server.root().call())["history_latest_ledger"]

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"*System Info*\n"
            f"Latest ledger: `{latest_ledger}`\n"
            f"Latest processed ledger: `{latest_processed_ledger}`\n"
            f"Left to process: `{latest_ledger - latest_processed_ledger}`"
        ),
        reply_to_message_id=update.message.message_id,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("add", add))
tg_app.add_handler(CommandHandler("remove", remove))
tg_app.add_handler(CommandHandler("enable", enable))
tg_app.add_handler(CommandHandler("disable", disable))
tg_app.add_handler(CommandHandler("system", system))

if __name__ == "__main__":
    loguru.logger.info("Starting bot...")
    tg_app.run_polling()
