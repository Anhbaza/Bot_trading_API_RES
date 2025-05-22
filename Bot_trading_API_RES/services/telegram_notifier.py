"""
Telegram notification service for Bot Trading API REST
Handles sending notifications and alerts via Telegram
"""

import asyncio
import logging
from typing import Optional, Union, Dict
from datetime import datetime
from telegram import Bot, ParseMode
from telegram.error import TelegramError

from ..core.models import SignalData, TradingPosition

class TelegramNotifier:
    def __init__(self, token: str = "", chat_id: str = ""):
        """
        Initialize Telegram notifier
        
        Parameters:
        -----------
        token : str
            Telegram bot token
        chat_id : str
            Telegram chat ID
        """
        self.token = token
        self.chat_id = chat_id
        self.bot = Bot(token=token)
        self.logger = logging.getLogger(__name__)
        self.message_queue = asyncio.Queue()
        self.is_running = False

    async def start(self):
        """Start the notification service"""
        self.is_running = True
        await self.process_message_queue()

    async def stop(self):
        """Stop the notification service"""
        self.is_running = False
        await self.message_queue.join()
        await self.bot.close()

    async def process_message_queue(self):
        """Process queued messages"""
        while self.is_running:
            try:
                if not self.message_queue.empty():
                    message = await self.message_queue.get()
                    await self._send_telegram_message(message)
                    self.message_queue.task_done()
                await asyncio.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error processing message queue: {str(e)}")

    async def _send_telegram_message(self, message: str):
        """
        Send message to Telegram
        
        Parameters:
        -----------
        message : str
            Message to send
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
        except TelegramError as e:
            self.logger.error(f"Telegram error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")

    async def send_message(self, message: str):
        """
        Queue message for sending
        
        Parameters:
        -----------
        message : str
            Message to send
        """
        await self.message_queue.put(message)

    async def send_signal(self, signal: SignalData):
        """
        Send trading signal notification
        
        Parameters:
        -----------
        signal : SignalData
            Trading signal data
        """
        message = (
            f"🚨 <b>Trading Signal</b>\n\n"
            f"Symbol: {signal.symbol}\n"
            f"Type: {signal.signal_type}\n"
            f"Entry: {signal.entry:.8f}\n"
            f"Stop Loss: {signal.stop_loss:.8f}\n"
            f"Take Profit: {signal.take_profit:.8f}\n"
            f"Confidence: {signal.confidence:.2f}\n"
            f"Time: {signal.timestamp}\n\n"
            f"Reason: {signal.reason}"
        )
        await self.send_message(message)

    async def send_position_update(self, position: TradingPosition):
        """
        Send position update notification
        
        Parameters:
        -----------
        position : TradingPosition
            Trading position data
        """
        message = (
            f"📊 <b>Position Update</b>\n\n"
            f"Symbol: {position.symbol}\n"
            f"Type: {position.position_type}\n"
            f"Entry: {position.entry_price:.8f}\n"
            f"Current: {position.current_price:.8f}\n"
            f"PnL: {position.pnl:.2f}%\n"
            f"Status: {position.status.value}"
        )
        await self.send_message(message)

    async def send_error(self, error: str):
        """
        Send error notification
        
        Parameters:
        -----------
        error : str
            Error message
        """
        message = (
            f"❌ <b>Error</b>\n\n"
            f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"Error: {error}"
        )
        await self.send_message(message)

    async def send_system_status(self, status: Dict):
        """
        Send system status notification
        
        Parameters:
        -----------
        status : Dict
            System status information
        """
        message = (
            f"📱 <b>System Status</b>\n\n"
            f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"Running: {status.get('is_running', False)}\n"
            f"Active Positions: {status.get('active_positions', 0)}\n"
            f"24h Volume: ${status.get('volume_24h', 0):,.2f}\n"
            f"24h PnL: {status.get('pnl_24h', 0):.2f}%"
        )
        await self.send_message(message)
