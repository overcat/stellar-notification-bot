# stellar-notification-bot

A simple bot that sends notifications to users when their Stellar account's balance changes.

## Usage

You can use the bot by sending a direct message to [@stellar_notification_bot](https://t.me/stellar_notification_bot) on
Telegram.

## Running the bot yourself

1. Create a `.env` file with the following variables:
    - `DEV_MODE (Optional)`: Set to `true` to run the bot in development mode
    - `BOT_TOKEN (Required)`: The token of your Telegram bot
    - `MONGODB_URI (Required)`: The URL of your MongoDB database
    - `DB_NAME (Optional)`: The name of your MongoDB database
    - `NETWORK_PASSPHRASE (Optional)`: The passphrase of the Stellar network you want to use
    - `HORIZON_URL (Optional)`: The URL of the Horizon server you want to use

2. Run the bot with docker-compose:
    ```bash
    docker-compose up -d
    ```

## Note:

- The not currently only listens to five types of operations: CreateAccount, AccountMerge, Payment,
  PathPaymentStrictSend and PathPaymentStrictReceive.