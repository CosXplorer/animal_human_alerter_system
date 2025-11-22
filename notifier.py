# notifier.py
import requests
import logging
import io

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str):
        url = f"{self.base}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        try:
            r = requests.post(url, json=payload, timeout=10)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.exception("Telegram send failed")
            return False

    def send_photo(self, image_bytes: bytes, caption: str = ""):
        """Send photo to Telegram with caption"""
        url = f"{self.base}/sendPhoto"
        files = {'photo': ('detection.jpg', image_bytes, 'image/jpeg')}
        data = {"chat_id": self.chat_id}
        if caption:
            data["caption"] = caption
            
        try:
            r = requests.post(url, files=files, data=data, timeout=15)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.exception("Telegram photo send failed")
            return False