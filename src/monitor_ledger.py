import time

import pika
from loguru import logger

from src.config import channel
from src.config import server
from src.db import SystemInfo


def get_transactions(ledger_id: int) -> list[str]:
    transactions = []
    builder = (
        server.transactions().for_ledger(ledger_id).include_failed(False).limit(50)
    )
    transactions += [
        record["envelope_xdr"] for record in builder.call()["_embedded"]["records"]
    ]
    while records := builder.next()["_embedded"]["records"]:
        transactions += [record["envelope_xdr"] for record in records]
    return transactions


def send_transactions(transactions: list[str]):
    channel.tx_select()
    for transaction in transactions:
        channel.basic_publish(
            exchange="",
            routing_key="snp-new-tx",
            body=transaction.encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    channel.tx_commit()


def monitor_ledger():
    latest_ledger = server.root().call()["history_latest_ledger"]
    logger.debug(f"latest_ledger: {latest_ledger}")
    processed_ledger = SystemInfo.get_processed_ledger()
    logger.debug(f"processed_ledger: {processed_ledger}")
    for ledger_id in range(processed_ledger + 1, latest_ledger + 1):
        logger.info(f"process ledger: {ledger_id}")
        transactions = get_transactions(ledger_id)
        send_transactions(transactions)
        SystemInfo.update_processed_ledger(ledger_id)


if __name__ == "__main__":
    logger.info("Start monitor ledger.")
    while True:
        try:
            monitor_ledger()
            time.sleep(10)
        except Exception as e:
            time.sleep(60)
