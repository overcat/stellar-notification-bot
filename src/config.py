import os
from dataclasses import dataclass

import pika
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


DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
MONGODB_URI = os.getenv("MONGODB_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_NAME = os.getenv("DB_NAME")

config = Config(
    dev_mode=DEV_MODE,
    mongodb_uri=MONGODB_URI,
    bot_token=BOT_TOKEN,
    db_name=DB_NAME,
)

# telegram
tg_app = ApplicationBuilder().token(config.bot_token).build()
# Stellar SDK
server = Server(horizon_url="https://horizon.stellar.org")

# RabbitMQ
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="",
        port=5672,
        credentials=pika.PlainCredentials("", ""),
    )
)
channel = connection.channel()
channel.queue_declare(queue="snp-new-tx")
