"""
Shared Telegram service for bot communication
Author: Anhbaza01
Last Updated: 2025-05-23 11:06:41
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode  # Thay đổi import này
from telegram.error import TelegramError

class TelegramService:
    def __init__(self, token: str, chat_id: str, bot_name: str):
        """
        Initialize Telegram service
        
        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID
            bot_name: Name of the bot using this service
        """
        self.bot = Bot(token=token)
        self.chat_id = chat_id
        self.bot_name = bot_name
        self.logger = logging.getLogger(f"{bot_name}.telegram")

    async def send_message(self, text: str, parse_mode: str = ParseMode.HTML) -> bool:
        """
        Send regular text message
        
        Args:
            text: Message text
            parse_mode: Message parse mode
            
        Returns:
            bool: True if successful
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except TelegramError as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False

    async def send_command(
        self, 
        command_type: str, 
        data: Dict[str, Any],
        silent: bool = False
    ) -> bool:
        """
        Send command message to other bot
        
        Args:
            command_type: Type of command
            data: Command data
            silent: If True, don't log errors
            
        Returns:
            bool: True if successful
        """
        try:
            message = {
                "type": command_type,
                "from": self.bot_name,
                "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                "data": data
            }
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"CMD:{json.dumps(message)}",
                parse_mode=ParseMode.HTML
            )
            return True
            
        except TelegramError as e:
            if not silent:
                self.logger.error(f"Error sending command: {str(e)}")
            return False

    @staticmethod
    def is_command_message(message: str) -> bool:
        """Check if message is a command"""
        return message.startswith("CMD:")

    @staticmethod
    def parse_command(message: str) -> Optional[Dict[str, Any]]:
        """
        Parse command from message
        
        Args:
            message: Raw message text
            
        Returns:
            Dict containing command data or None if invalid
        """
        try:
            if not message.startswith("CMD:"):
                return None
            
            data = json.loads(message[4:])
            
            # Validate required fields
            required_fields = ["type", "from", "timestamp", "data"]
            if not all(field in data for field in required_fields):
                return None
                
            return data
            
        except (json.JSONDecodeError, KeyError):
            return None

    async def send_error(self, error: str) -> bool:
        """Send error message"""
        return await self.send_message(
            f"❌ Lỗi: {error}",
            parse_mode=ParseMode.HTML
        )

    async def send_warning(self, warning: str) -> bool:
        """Send warning message"""
        return await self.send_message(
            f"⚠️ Cảnh báo: {warning}",
            parse_mode=ParseMode.HTML
        )

    async def send_success(self, message: str) -> bool:
        """Send success message"""
        return await self.send_message(
            f"✅ {message}",
            parse_mode=ParseMode.HTML
        )
