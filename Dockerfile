FROM python:3.11

ENV STELLAR_SDK_RUNTIME_TYPE_CHECKING=0
ENV DEV_MODE=false
ENV MONGODB_URI=""
ENV BOT_TOKEN=""
ENV DB_NAME=stellar_notification_bot
ENV NETWORK_PASSPHRASE="Public Global Stellar Network ; September 2015"
ENV HORIZON_URL="https://horizon.stellar.org"

COPY . /app

WORKDIR /app

RUN pip install -r requirements.lock

CMD ["python", "src/bot.py"]