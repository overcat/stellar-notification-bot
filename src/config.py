import os
from dataclasses import dataclass

from dotenv import load_dotenv
from stellar_sdk import Server
from telegram.ext import ApplicationBuilder

load_dotenv()


@dataclass
class Config:
    dev_mode: bool
    mongodb_uri: str
    bot_token: str
    db_name: str
    network_passphrase: str


DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
MONGODB_URI = os.getenv("MONGODB_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_NAME = os.getenv("DB_NAME", "stellar_notification_bot")

if MONGODB_URI is None:
    raise ValueError("MONGODB_URI is not set")

if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN is not set")

config = Config(
    dev_mode=DEV_MODE,
    mongodb_uri=MONGODB_URI,
    bot_token=BOT_TOKEN,
    db_name=DB_NAME,
    network_passphrase="Public Global Stellar Network ; September 2015",
)

# telegram
tg_app = ApplicationBuilder().token(config.bot_token).build()
# Stellar SDK
server = Server(horizon_url="https://horizon.stellar.org")
