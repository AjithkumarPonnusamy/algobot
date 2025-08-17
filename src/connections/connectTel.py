import requests
import os
from dotenv import load_dotenv
load_dotenv(".env")
# Replace with your actual token and chat id
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") # from getUpdates after you message the bot

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"  # optional: allows formatting like <b>bold</b>
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Message sent!")
        else:
            print("❌ Failed to send message:", response.text)
    except Exception as e:
        print("❌ Exception:", e)


# Example usage
# send_telegram_message("🚀 Strategy started at 9:15 AM.")
