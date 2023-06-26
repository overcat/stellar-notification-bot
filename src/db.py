from __future__ import annotations

import asyncio
import datetime
from typing import Optional

import loguru
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore[import]
from pydantic import BaseModel, Field
from stellar_sdk import ServerAsync

from src.config import config

client: AsyncIOMotorClient = AsyncIOMotorClient(config.mongodb_uri)
db = client[config.db_name]


class Chat(BaseModel):
    chat_id: int
    account_ids: list[str]
    enable: bool = True
    created_time: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)

    @staticmethod
    async def get_chat_ids_by_enable(account_ids: list[str]) -> list[int]:
        return [
            chat["chat_id"]
            async for chat in db.chat.find(
                {"$or": [{"account_ids": acc} for acc in account_ids], "enable": True},
                {"chat_id": 1, "_id": 0},
            )
        ]

    @staticmethod
    async def new_chat(chat_id: int) -> None:
        if not Chat.is_chat_id_exist(chat_id):
            await db.chat.insert_one(Chat(chat_id=chat_id, account_ids=list()).dict())
        else:
            await Chat.enable_notification(chat_id)

    @staticmethod
    async def add_stellar_account(chat_id: int, account_id: str) -> None:
        await db.chat.update_one(
            {"chat_id": chat_id}, {"$addToSet": {"account_ids": account_id}}
        )

    @staticmethod
    async def remove_stellar_account(chat_id: int, account_id: str) -> None:
        await db.chat.update_one(
            {"chat_id": chat_id}, {"$pull": {"account_ids": account_id}}
        )

    @staticmethod
    async def disable_notification(chat_id: int) -> None:
        await db.chat.update_one({"chat_id": chat_id}, {"$set": {"enable": False}})

    @staticmethod
    async def enable_notification(chat_id: int) -> None:
        await db.chat.update_one({"chat_id": chat_id}, {"$set": {"enable": True}})

    @staticmethod
    async def is_chat_id_exist(chat_id: int) -> bool:
        return (await db.chat.find_one({"chat_id": chat_id})) is not None


class SystemInfo(BaseModel):
    processed_ledger: int = 0

    @staticmethod
    async def update_processed_ledger(ledger: int) -> None:
        if db.system_info.find_one() is None:
            await db.system_info.insert_one(SystemInfo(processed_ledger=ledger).dict())
        else:
            await db.system_info.update_one({}, {"$set": {"processed_ledger": ledger}})

    @staticmethod
    async def get_processed_ledger() -> int:
        info = await db.system_info.find_one({}, {"processed_ledger": 1, "_id": 0})
        if info is None:
            raise SystemError(
                "processed_ledger is 0, start from 0 will cost a lot of time, set a proper value in db."
            )
        return info["processed_ledger"]

    @staticmethod
    async def init_processed_ledger() -> None:
        async with ServerAsync(config.horizon_url) as server:
            latest_ledger = (await server.root().call())["history_latest_ledger"]
        if db.system_info.find_one({}) is not None:
            loguru.logger.info("processed_ledger is not 0, skip init.")
            return
        await SystemInfo.update_processed_ledger(latest_ledger)
        loguru.logger.info(f"init processed_ledger to {latest_ledger}")


class Message(BaseModel):
    id: Optional[ObjectId] = Field(alias="_id")
    content: str
    chat_id: int
    created_time: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)

    class Config:
        arbitrary_types_allowed = True

    @staticmethod
    async def new_messages(messages: list["Message"]) -> None:
        if not messages:
            return
        await db.message.insert_many([message.dict() for message in messages])

    @classmethod
    async def get_oldest_unsent_message(cls) -> Optional[Message]:
        record = await db.message.find_one({}, sort=[("created_time", 1)])
        if not record:
            return None
        return cls(**record)

    async def remove(self):
        await db.message.delete_one({"_id": self.id})


# Init DB
if __name__ == "__main__":
    # asyncio.run(SystemInfo.init_processed_ledger())
    t = asyncio.run(
        Chat.get_chat_ids_by_enable(
            [
                "GDBUD2ENGO677J3K64AMPRS6ECGDMATTJJWILPOHRQ56UYFF5USCC7KT",
                "GBKEE4AZUJG3NDGUTVM35U22W24GEYCMWLSOGCV7KVKGOT25IAHK7EOR",
            ]
        )
    )
    print(t)
