from telegram import Bot
from telegram.error import TelegramError
import logging
from datetime import datetime

class TelegramService:
    def __init__(self, token: str, chat_id: str):
        self.bot = Bot(token=token)
        self.chat_id = chat_id
        self.logger = logging.getLogger('TelegramService')

    async def send_message(self, text: str) -> bool:
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode='HTML'
            )
            return True
        except TelegramError as e:
            self.logger.error(f"Failed to send message: {str(e)}")
            return False

    async def test_connection(self) -> bool:
        try:
            await self.bot.get_me()
            test_msg = (
                f"🤖 Bot connection test\n"
                f"⌚ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
            return await self.send_message(test_msg)
        except Exception as e:
            self.logger.error(f"Telegram test failed: {str(e)}")
            return False