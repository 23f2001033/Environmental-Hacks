"""Point the Telegram bot at the deployed webhook and set its commands. Run after every deploy that changes the URL."""

from _common import outputs, secret, telegram

url = outputs()["WebhookUrl"]
r = telegram("setWebhook", url=url, secret_token=secret("/jalsaathi/telegram/webhook-secret"),
             allowed_updates=["message", "callback_query"], drop_pending_updates=True)
print("setWebhook:", r.get("ok"), r.get("description"))
telegram("setMyCommands", commands=[
    {"command": "status", "description": "गाँव के पानी की स्थिति / Water status"},
    {"command": "english", "description": "Messages in English"},
    {"command": "hindi", "description": "संदेश हिंदी में"},
    {"command": "stop", "description": "सदस्यता बंद करें / Stop and delete my data"},
    {"command": "help", "description": "मदद / Help"},
])
telegram("setMyDescription", description=("JalSaathi: सरकारी लैब जांच में आपके गाँव का पानी असुरक्षित पाया जाए तो सूचना, "
                                          "सही सावधानी, और ठीक होने तक मामले पर नज़र। Hindi and English: send /english."))
info = telegram("getWebhookInfo")["result"]
print("webhook:", info.get("url") == url, "pending:", info.get("pending_update_count"), "last error:", info.get("last_error_message"))
