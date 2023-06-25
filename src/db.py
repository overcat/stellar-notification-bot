from __future__ import annotations

import datetime

from pydantic import BaseModel
from pymongo import MongoClient

from src.config import config, server

client = MongoClient(config.mongodb_uri)
db = client[config.db_name]


class Chat(BaseModel):
    chat_id: int
    account_ids: list[str]
    enable: bool = True
    first_sign_up_time: datetime.datetime = datetime.datetime.now(
        tz=datetime.timezone.utc
    )

    @staticmethod
    def get_chat_ids(account_ids: list[str]) -> list[int]:
        chats = db.user.find(
            {"$or": [{"account_ids": acc} for acc in account_ids]},
            {"chat_id": 1, "_id": 0},
        )
        return [chat["chat_id"] for chat in chats]

    @staticmethod
    def new_chat(chat_id: int) -> None:
        if not Chat.is_chat_id_exist(chat_id):
            db.chat.insert_one(Chat(chat_id=chat_id, account_ids=set()).dict())
        else:
            Chat.enable_notification(chat_id)

    @staticmethod
    def add_stellar_account(chat_id: int, account_id: str) -> None:
        db.chat.update_one(
            {"chat_id": chat_id}, {"$addToSet": {"account_ids": account_id}}
        )

    @staticmethod
    def remove_stellar_account(chat_id: int, account_id: str) -> None:
        db.chat.update_one({"chat_id": chat_id}, {"$pull": {"account_ids": account_id}})

    @staticmethod
    def disable_notification(chat_id: int) -> None:
        db.chat.update_one({"chat_id": chat_id}, {"$set": {"enable": False}})

    @staticmethod
    def enable_notification(chat_id: int) -> None:
        db.chat.update_one({"chat_id": chat_id}, {"$set": {"enable": True}})

    @staticmethod
    def is_chat_id_exist(chat_id: int) -> bool:
        return db.chat.find_one({"chat_id": chat_id}) is not None


class SystemInfo(BaseModel):
    processed_ledger: int = 0

    @staticmethod
    def update_processed_ledger(ledger: int) -> None:
        if db.system_info.find_one() is None:
            db.system_info.insert_one(SystemInfo(processed_ledger=ledger).dict())
        else:
            db.system_info.update_one({}, {"$set": {"processed_ledger": ledger}})

    @staticmethod
    def get_processed_ledger() -> int:
        info = db.system_info.find_one({}, {"processed_ledger": 1, "_id": 0})
        if info is None:
            raise SystemError(
                "processed_ledger is 0, start from 0 will cost a lot of time, set a proper value in db."
            )
        return info["processed_ledger"]

    @staticmethod
    def init_processed_ledger() -> None:
        latest_ledger = server.root().call()["history_latest_ledger"]
        if db.system_info.find_one() is not None:
            print("processed_ledger is not 0, skip init.")
        SystemInfo.update_processed_ledger(latest_ledger)


if __name__ == "__main__":
    SystemInfo.init_processed_ledger()
