#!/usr/bin/env python3
"""
Telegram Service for Bot Communication
Author: Anhbaza01
Version: 1.0.0
Last Updated: 2025-05-23 20:11:58 UTC
"""

import logging
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

class TelegramService:
    def __init__(
        self, 
        token: str, 
        chat_id: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Telegram Service
        
        Parameters:
            token (str): Telegram Bot token
            chat_id (str): Chat ID to send messages to
            logger (Logger): Optional logger instance
        """
        self.token = token
        self.chat_id = chat_id
        self.logger = logger or logging.getLogger(__name__)
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.user = "Anhbaza01"

    async def send_message(self, text: str) -> bool:
        """Send text message to Telegram"""
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    self.logger.info(
                        f"HTTP Request: POST {url} \"{response.status} {response.reason}\""
                    )
                    
                    if response.status == 200:
                        return True
                    else:
                        self.logger.error(
                            f"[-] Telegram API error: {response.status} {response.reason}"
                        )
                        return False
                        
        except Exception as e:
            self.logger.error(f"[-] Error sending Telegram message: {str(e)}")
            return False

    async def send_signal(self, signal: Dict[str, Any]) -> bool:
        """Send trading signal notification"""
        try:
            # Format message
            message = (
                f"🚨 <b>New Trading Signal</b>\n\n"
                f"Symbol: {signal['symbol']}\n"
                f"Type: {signal['type']}\n"
                f"Entry: {signal['entry']:.8f}\n"
                f"Take Profit: {signal['tp']:.8f}\n"
                f"Stop Loss: {signal['sl']:.8f}\n"
                f"RSI: {signal['rsi']:.2f}\n"
                f"Confidence: {signal.get('confidence', 0)}%\n\n"
                f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"User: {self.user}"
            )
            
            return await self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"[-] Error sending signal notification: {str(e)}")
            return False

    async def send_error(self, error: str) -> bool:
        """Send error notification"""
        try:
            message = (
                f"❌ <b>Error</b>\n\n"
                f"{error}\n\n"
                f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"User: {self.user}"
            )
            
            return await self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"[-] Error sending error notification: {str(e)}")
            return False

    async def test_connection(self) -> bool:
        """Test Telegram connection"""
        try:
            # Get bot info
            url = f"{self.api_url}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url) as response:
                    self.logger.info(
                        f"HTTP Request: POST {url} \"{response.status} {response.reason}\""
                    )
                    
                    if response.status == 200:
                        data = await response.json()
                        bot_name = data['result']['username']
                        self.logger.info(f"[+] Connected to Telegram as {bot_name}")
                        
                        # Send test message
                        test_message = (
                            f"🤖 Bot Connected\n"
                            f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                            f"User: {self.user}"
                        )
                        return await self.send_message(test_message)
                    else:
                        self.logger.error(
                            f"[-] Telegram API error: {response.status} {response.reason}"
                        )
                        return False
                        
        except Exception as e:
            self.logger.error(f"[-] Error testing Telegram connection: {str(e)}")
            return False