import asyncio
from decimal import Decimal
from loguru import logger
from stellar_sdk import (
    parse_transaction_envelope_from_xdr,
    FeeBumpTransactionEnvelope,
    AccountMerge,
    Payment,
    PathPaymentStrictSend,
    PathPaymentStrictReceive,
    MuxedAccount,
    Asset,
    CreateAccount,
    ServerAsync,
)

from src.config import config
from src.db import SystemInfo, Message, Chat


def format_asset(asset: Asset) -> str:
    if asset.is_native():
        return "XLM"
    else:
        assert asset.issuer is not None
        return f"{asset.code}({asset.issuer[:4]}...{asset.issuer[-4:]})"


def format_number(num_str: str) -> str:
    int_part = num_str.split(".", 1)[0]
    if len(int_part) > 3:
        segments: list[str] = []
        while len(int_part) > 0:
            segment = int_part[-3:]
            segments.insert(0, segment)
            int_part = int_part[:-3]
        int_part = ",".join(segments)
    dec_part = ""
    if "." in num_str:
        dec_part = num_str.split(".", 1)[1]
        dec_part = "." + dec_part
    return int_part + dec_part


async def get_transactions(ledger_id: int) -> list[str]:
    transactions = []
    async with ServerAsync(config.horizon_url) as server:
        builder = (
            server.transactions().for_ledger(ledger_id).include_failed(False).limit(200)
        )
        transactions += [
            record["envelope_xdr"]
            for record in (await builder.call())["_embedded"]["records"]
        ]
        while records := (await builder.next())["_embedded"]["records"]:
            transactions += [record["envelope_xdr"] for record in records]
        return transactions


async def build_create_account_messages(
    op: CreateAccount, tx_hash: str, tx_source: MuxedAccount
) -> list[Message]:
    from_ = op.source.account_id if op.source else tx_source.account_id
    to = op.destination
    text = (
        "*Create Account*\n"
        f"From: `{from_}`\n"
        f"To: `{to}`\n"
        f"Amount: `{format_number(op.starting_balance)} XLM`\n"
    )
    chat_ids = await Chat.get_chat_ids_by_enable([from_, to])
    messages = [
        Message(chat_id=chat_id, content=text, tx_hash=tx_hash) for chat_id in chat_ids
    ]
    return messages


async def build_account_merge_messages(
    op: AccountMerge, tx_hash: str, tx_source: MuxedAccount
) -> list[Message]:
    from_ = op.source.account_id if op.source else tx_source.account_id
    to = op.destination.account_id
    text = "*Account Merge*\n" f"Account: `{from_}`\n" f"Merge to: `{to}`\n"
    chat_ids = await Chat.get_chat_ids_by_enable([from_, to])
    messages = [
        Message(chat_id=chat_id, content=text, tx_hash=tx_hash) for chat_id in chat_ids
    ]
    return messages


def hit_payment_filter(op: Payment):
    if op.asset.is_native() and Decimal(op.amount) < Decimal("0.01"):
        return True

    if op.asset == Asset(
        "AQUA", "GBNZILSTVQZ4R7IKQDGHYGY2QXL5QOFJYQMXPKWRRM5PAV7Y4M67AQUA"
    ) and Decimal(op.amount) < Decimal("100"):
        return True

    if op.asset == Asset(
        "USDC", "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN"
    ) and Decimal(op.amount) < Decimal("0.01"):
        return True
    return False


async def build_payment_messages(
    op: Payment, tx_hash: str, tx_source: MuxedAccount
) -> list[Message]:
    if config.ignore_tiny_payment and hit_payment_filter(op):
        return []
    from_ = op.source.account_id if op.source else tx_source.account_id
    to = op.destination.account_id
    text = (
        "*Payment*\n"
        f"From: `{from_}`\n"
        f"To: `{to}`\n"
        f"Amount: `{format_number(op.amount)} {format_asset(op.asset)}`\n"
    )
    chat_ids = await Chat.get_chat_ids_by_enable([from_, to])
    messages = [
        Message(chat_id=chat_id, content=text, tx_hash=tx_hash) for chat_id in chat_ids
    ]
    return messages


async def build_path_payment_strict_send_messages(
    op: PathPaymentStrictSend, tx_hash: str, tx_source: MuxedAccount
) -> list[Message]:
    from_ = op.source.account_id if op.source else tx_source.account_id
    to = op.destination.account_id
    text = (
        "*Path Payment Strict Send*\n"
        f"From: `{from_}`\n"
        f"Destination: `{to}`\n"
        f"Send Amount: `{format_number(op.send_amount)} {format_asset(op.send_asset)}`\n"
        f"Destination Min Receive Amount: `{format_number(op.dest_min)} {format_asset(op.dest_asset)}`\n"
    )
    chat_ids = await Chat.get_chat_ids_by_enable([from_, to])
    messages = [
        Message(chat_id=chat_id, content=text, tx_hash=tx_hash) for chat_id in chat_ids
    ]
    return messages


async def build_path_payment_strict_receive_messages(
    op: PathPaymentStrictReceive, tx_hash: str, tx_source: MuxedAccount
) -> list[Message]:
    from_ = op.source.account_id if op.source else tx_source.account_id
    to = op.destination.account_id
    text = (
        "*Path Payment Strict Receive*\n"
        f"From: `{from_}`\n"
        f"Destination: `{to}`\n"
        f"Send Max Amount: `{format_number(op.send_max)} {format_asset(op.send_asset)}`\n"
        f"Destination Receive: `{format_number(op.dest_amount)} {format_asset(op.dest_asset)}`\n"
    )
    chat_ids = await Chat.get_chat_ids_by_enable([from_, to])
    messages = [
        Message(chat_id=chat_id, content=text, tx_hash=tx_hash) for chat_id in chat_ids
    ]
    return messages


async def save_messages(transactions: list[str]) -> None:
    messages = []
    for transaction in transactions:
        try:
            te = parse_transaction_envelope_from_xdr(
                transaction, config.network_passphrase
            )
        except Exception as e:
            logger.error(f"parse transaction error: {e}")
            continue

        if isinstance(te, FeeBumpTransactionEnvelope):
            continue

        tx = te.transaction
        for op in tx.operations:
            if isinstance(op, AccountMerge):
                messages += await build_account_merge_messages(
                    op, te.hash_hex(), tx.source
                )
            elif isinstance(op, CreateAccount):
                messages += await build_create_account_messages(
                    op, te.hash_hex(), tx.source
                )
            elif isinstance(op, Payment):
                messages += await build_payment_messages(op, te.hash_hex(), tx.source)
            elif isinstance(op, PathPaymentStrictSend):
                messages += await build_path_payment_strict_send_messages(
                    op, te.hash_hex(), tx.source
                )
            elif isinstance(op, PathPaymentStrictReceive):
                messages += await build_path_payment_strict_receive_messages(
                    op, te.hash_hex(), tx.source
                )
    await Message.new_messages(messages)


async def monitor_ledger():
    while True:
        async with ServerAsync(config.horizon_url) as server:
            latest_ledger = (await server.root().call())["history_latest_ledger"]
            logger.info(f"latest_ledger: {latest_ledger}")
        processed_ledger = await SystemInfo.get_processed_ledger()
        logger.info(f"processed_ledger: {processed_ledger}")
        if processed_ledger >= latest_ledger:
            await asyncio.sleep(3)
            continue
        for ledger_id in range(processed_ledger + 1, latest_ledger + 1):
            logger.info(f"process ledger: {ledger_id}")
            transactions = await get_transactions(ledger_id)
            await save_messages(transactions)
            await SystemInfo.update_processed_ledger(ledger_id)


if __name__ == "__main__":
    logger.info("Start monitor ledger.")
    asyncio.run(monitor_ledger())
