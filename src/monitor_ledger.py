import time

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
)

from src.config import server, config
from src.db import SystemInfo, Message, Chat


def format_asset(asset: Asset) -> str:
    if asset.is_native():
        return "XLM"
    else:
        assert asset.issuer is not None
        return f"{asset.code}({asset.issuer[-4:]})"


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


def get_transactions(ledger_id: int) -> list[str]:
    transactions = []
    builder = (
        server.transactions().for_ledger(ledger_id).include_failed(False).limit(200)
    )
    transactions += [
        record["envelope_xdr"] for record in builder.call()["_embedded"]["records"]
    ]
    while records := builder.next()["_embedded"]["records"]:
        transactions += [record["envelope_xdr"] for record in records]
    return transactions


def build_create_account_messages(
    op: CreateAccount, tx_hash: str, tx_source: MuxedAccount
) -> list[Message]:
    from_ = op.source.account_id if op.source else tx_source.account_id
    to = op.destination
    text = (
        "*Create Account*\n"
        f"From: `{from_}`\n"
        f"To: `{to}`\n"
        f"Amount: `{format_number(op.starting_balance)} XLM`\n"
        f"[View on StellarExpert](https://stellar\\.expert/explorer/public/tx/{tx_hash})"
    )
    chat_ids = Chat.get_chat_ids([from_, to])
    messages = [Message(chat_id=chat_id, content=text) for chat_id in chat_ids]
    return messages


def build_account_merge_messages(
    op: AccountMerge, tx_hash: str, tx_source: MuxedAccount
) -> list[Message]:
    from_ = op.source.account_id if op.source else tx_source.account_id
    to = op.destination.account_id
    text = (
        "*Account Merge*\n"
        f"Account: `{from_}`\n"
        f"Merge to: `{to}`\n"
        f"[View on StellarExpert](https://stellar\\.expert/explorer/public/tx/{tx_hash})"
    )
    chat_ids = Chat.get_chat_ids([from_, to])
    messages = [Message(chat_id=chat_id, content=text) for chat_id in chat_ids]
    return messages


def build_payment_messages(
    op: Payment, tx_hash: str, tx_source: MuxedAccount
) -> list[Message]:
    from_ = op.source.account_id if op.source else tx_source.account_id
    to = op.destination.account_id
    text = (
        "*Payment*\n"
        f"From: `{from_}`\n"
        f"To: `{to}`\n"
        f"Amount: `{format_number(op.amount)} {format_asset(op.asset)}`\n"
        f"[View on StellarExpert](https://stellar\\.expert/explorer/public/tx/{tx_hash})"
    )
    chat_ids = Chat.get_chat_ids([from_, to])
    messages = [Message(chat_id=chat_id, content=text) for chat_id in chat_ids]
    return messages


def build_path_payment_strict_send_messages(
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
        f"[View on StellarExpert](https://stellar\\.expert/explorer/public/tx/{tx_hash})"
    )
    chat_ids = Chat.get_chat_ids([from_, to])
    messages = [Message(chat_id=chat_id, content=text) for chat_id in chat_ids]
    return messages


def build_path_payment_strict_receive_messages(
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
        f"[View on StellarExpert](https://stellar\\.expert/explorer/public/tx/{tx_hash})"
    )
    chat_ids = Chat.get_chat_ids([from_, to])
    messages = [Message(chat_id=chat_id, content=text) for chat_id in chat_ids]
    return messages


def save_messages(transactions: list[str]) -> None:
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
                messages += build_account_merge_messages(op, te.hash_hex(), tx.source)
            elif isinstance(op, CreateAccount):
                messages += build_create_account_messages(op, te.hash_hex(), tx.source)
            elif isinstance(op, Payment):
                messages += build_payment_messages(op, te.hash_hex(), tx.source)
            elif isinstance(op, PathPaymentStrictSend):
                messages += build_path_payment_strict_send_messages(
                    op, te.hash_hex(), tx.source
                )
            elif isinstance(op, PathPaymentStrictReceive):
                messages += build_path_payment_strict_receive_messages(
                    op, te.hash_hex(), tx.source
                )
    Message.new_messages(messages)


def monitor_ledger():
    latest_ledger = server.root().call()["history_latest_ledger"]
    logger.info(f"latest_ledger: {latest_ledger}")
    processed_ledger = SystemInfo.get_processed_ledger()
    logger.info(f"processed_ledger: {processed_ledger}")
    for ledger_id in range(processed_ledger + 1, latest_ledger + 1):
        logger.info(f"process ledger: {ledger_id}")
        transactions = get_transactions(ledger_id)
        save_messages(transactions)
        SystemInfo.update_processed_ledger(ledger_id)


if __name__ == "__main__":
    logger.info("Start monitor ledger.")
    while True:
        try:
            monitor_ledger()
            time.sleep(2)
        except Exception as e:
            time.sleep(60)
