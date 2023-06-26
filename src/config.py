import os
from dataclasses import dataclass

import loguru
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
HORIZON_URL = os.getenv("HORIZON_URL")
NETWORK_PASSPHRASE = os.getenv("NETWORK_PASSPHRASE")

if DEV_MODE:
    loguru.logger.info("Running in dev mode")
    loguru.logger.info(f"Env: {os.environ}")

if MONGODB_URI is None:
    raise ValueError("MONGODB_URI is not set")

if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN is not set")

if HORIZON_URL is None:
    raise ValueError("HORIZON_URL is not set")

if NETWORK_PASSPHRASE is None:
    raise ValueError("NETWORK_PASSPHRASE is not set")

config = Config(
    dev_mode=DEV_MODE,
    mongodb_uri=MONGODB_URI,
    bot_token=BOT_TOKEN,
    db_name=DB_NAME,
    network_passphrase=NETWORK_PASSPHRASE,
)

# telegram
tg_app = ApplicationBuilder().token(config.bot_token).build()
# Stellar SDK
server = Server(horizon_url=HORIZON_URL)
