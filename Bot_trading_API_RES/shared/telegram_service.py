#!/usr/bin/env python3
"""
Telegram Service Module
Author: Anhbaza01
Version: 1.0.0
Last Updated: 2025-05-23 19:19:10 UTC
"""

import logging
import asyncio
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

class TelegramService:
    def __init__(self, token: str, chat_id: str):
        """Initialize Telegram service"""
        self.token = token
        self.chat_id = chat_id
        self.bot = Bot(token=token)
        self.logger = logging.getLogger(__name__)

    async def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        try:
            me = await self.bot.get_me()
            self.logger.info(f"Connected to Telegram as {me.username}")
            return True
        except TelegramError as e:
            self.logger.error(f"Telegram connection error: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Error testing Telegram connection: {str(e)}")
            return False

    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram channel"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            return True
        except TelegramError as e:
            self.logger.error(f"Error sending Telegram message: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending message: {str(e)}")
            return False

    async def send_startup_message(self, user: str) -> bool:
        """Send bot startup notification"""
        message = f"""
🚀 <b>Bot Trading khởi động</b>
👤 User: {user}
⚙️ Đang quét thị trường...
"""
        return await self.send_message(message)

    async def send_error_message(self, error: str) -> bool:
        """Send error notification"""
        message = f"""
❌ <b>Lỗi hệ thống</b>
⚠️ {error}
"""
        return await self.send_message(message)