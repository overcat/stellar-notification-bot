import asyncio

from loguru import logger
from stellar_sdk import (
    parse_transaction_envelope_from_xdr,
    FeeBumpTransactionEnvelope,
    Payment,
    PathPaymentStrictSend,
    PathPaymentStrictReceive,
    AccountMerge,
)

from src.config import channel, tg_app
from src.db import Chat


def format_number(num_str: str) -> str:
    int_part = num_str.split(".", 1)[0]
    if len(int_part) > 3:
        segments = []
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


def send_telegram_message(from_: str, to: str, text: str):
    ids = Chat.get_chat_ids([from_, to])
    # TODO: send message to all chat_ids in one request?
    for chat_id in ids:
        asyncio.run(tg_app.bot.send_message(
            chat_id=chat_id,
            text=text,
        ))


def consume_transaction(ch, method, properties, body):
    logger.debug(f"receive transaction: {body}")
    try:
        te = parse_transaction_envelope_from_xdr(
            body.decode("utf-8"), ""
        )  # we don't care about network
    except Exception as e:
        logger.error(f"parse transaction error: {e}")
        return

    if isinstance(te, FeeBumpTransactionEnvelope):
        return

    tx = te.transaction
    for op in tx.operations:
        valid_op = False
        if isinstance(op, AccountMerge):
            from_ = op.source.account_id if op.source else tx.source.account_id
            to = op.destination.account_id
            valid_op = True
        if isinstance(op, Payment):
            text = f"{op.source.account_id} send {format_number(op.amount)} {op.asset.code} to {op.destination.account_id}"
            to = op.destination.account_id
            valid_op = True
        if isinstance(op, PathPaymentStrictSend):
            text = f"{op.source.account_id} path send {format_number(op.amount)} {op.send_asset.code} to {op.destination.account_id}"
            to = op.destination.account_id
            valid_op = True
        if isinstance(op, PathPaymentStrictReceive):
            text = f"{op.source.account_id} path send {format_number(op.amount)} {op.send_asset.code} from {op.destination.account_id}"
            to = op.destination.account_id
            valid_op = True
        if valid_op:

            send_telegram_message(from_, to, text)


channel.basic_consume(
    queue="snp-new-tx", auto_ack=True, on_message_callback=consume_transaction
)
channel.start_consuming()
