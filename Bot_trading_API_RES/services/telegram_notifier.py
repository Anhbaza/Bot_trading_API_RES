"""
Telegram notification service
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
import telegram

class TelegramNotifier:
    def __init__(self, token: str = "", chat_id: str = ""):
        """Initialize Telegram notifier
        
        Parameters
        ----------
        token : str
            Telegram bot token
        chat_id : str
            Telegram chat ID to send messages to
        """
        if not token or not chat_id:
            raise ValueError("Telegram token and chat ID are required")
            
        self.token = token
        self.chat_id = chat_id
        self.bot: Optional[Bot] = None
        self.logger = logging.getLogger(__name__)
        self.message_queue = asyncio.Queue()
        self.is_running = False
        self.last_message_time = datetime.utcnow()
        self.MESSAGE_RATE_LIMIT = 1.0  # Minimum seconds between messages
        
    async def start(self):
        """Start the notification service"""
        try:
            self.logger.info("Starting Telegram notification service...")
            self.is_running = True
            
            # Initialize bot
            self.bot = Bot(self.token)
            
            # Test bot connection
            me = await self.bot.get_me()
            self.logger.info(f"Bot connected successfully: @{me.username}")
            
            # Test chat ID
            try:
                chat = await self.bot.get_chat(self.chat_id)
                self.logger.info(f"Chat found: {chat.type} - {chat.title if chat.type != 'private' else 'Private'}")
            except telegram.error.BadRequest as e:
                self.logger.error(f"Error getting chat: {str(e)}")
                raise
                
            self.logger.info("Telegram notification service started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Telegram service: {str(e)}")
            self.is_running = False
            raise

    async def stop(self):
        """Stop the notification service"""
        try:
            self.logger.info("Stopping Telegram notification service...")
            self.is_running = False
            # Empty the message queue
            while not self.message_queue.empty():
                try:
                    self.message_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            self.logger.info("Telegram notification service stopped")
        except Exception as e:
            self.logger.error(f"Error stopping Telegram service: {str(e)}")

    async def send_message(self, message: str) -> bool:
        """Send message to Telegram chat
        
        Parameters
        ----------
        message : str
            Message to send
            
        Returns
        -------
        bool
            True if message was sent successfully
        """
        if not self.is_running or not self.bot:
            self.logger.error("Telegram service is not running")
            return False
            
        try:
            self.logger.debug(f"Sending message to chat {self.chat_id}")
            await self._handle_rate_limit()
            
            result = await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            
            self.logger.debug(f"Message sent successfully. Message ID: {result.message_id}")
            return True
            
        except telegram.error.Unauthorized:
            self.logger.error("Bot token is invalid or bot was blocked")
            return False
        except telegram.error.BadRequest as e:
            self.logger.error(f"Bad request: {str(e)}")
            if "chat not found" in str(e).lower():
                self.logger.error(f"Chat ID {self.chat_id} not found. Did you start the bot?")
            return False
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False

    async def send_signal(self, signal_data) -> bool:
        """Send trading signal
        
        Parameters
        ----------
        signal_data : SignalData
            Signal data to send
            
        Returns
        -------
        bool
            True if signal was sent successfully
        """
        try:
            message = (
                f"🚨 <b>{signal_data.signal_type} Signal</b>\n\n"
                f"💎 Coin: {signal_data.symbol}\n"
                f"📈 Entry: ${signal_data.entry:,.8f}\n"
                f"🛑 Stop Loss: ${signal_data.stop_loss:,.8f}\n"
                f"🎯 Take Profit: ${signal_data.take_profit:,.8f}\n"
                f"⭐ Confidence: {signal_data.confidence:.2f}\n\n"
                f"📝 Lý do:\n{signal_data.reason}\n\n"
                f"⏰ Time: {signal_data.timestamp}"
            )
            
            return await self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"Error sending signal: {str(e)}")
            return False

    async def _handle_rate_limit(self):
        """Handle message rate limiting"""
        now = datetime.utcnow()
        elapsed = (now - self.last_message_time).total_seconds()
        if elapsed < self.MESSAGE_RATE_LIMIT:
            delay = self.MESSAGE_RATE_LIMIT - elapsed
            await asyncio.sleep(delay)
        self.last_message_time = now