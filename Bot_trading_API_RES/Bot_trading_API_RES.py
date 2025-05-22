#!/usr/bin/env python3
"""
Bot Trading API REST - Main Entry Point
Author: Anhbaza
Date: 2025-05-22 18:18:30
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from binance import Client

from config.logging_config import setup_logging
from services.telegram_notifier import TelegramNotifier
from core.analyzer.futures import FuturesAnalyzer

# Load environment variables
load_dotenv('data.env')

class TradingBot:
    def __init__(self):
        self.logger = setup_logging()
        self.settings: Dict = {}
        self.notifier: Optional[TelegramNotifier] = None
        self.analyzer: Optional[FuturesAnalyzer] = None
        self.client: Optional[Client] = None
        self._cleanup_done = False
        self._is_running = True

        async def startup(self):
         """Initialize bot components"""
         try:
            # Load settings
            self.logger.info("Loading configuration...")
            self.settings = load_settings()
            
            # Initialize Binance client
            self.client = Client(
                self.settings['BINANCE_API_KEY'],
                self.settings['BINANCE_API_SECRET']
            )
            
            # Test API connection
            self.client.ping()
            self.logger.info("Successfully connected to Binance API")

            # Initialize components
            self.notifier = TelegramNotifier(
                token=self.settings['TELEGRAM_BOT_TOKEN'],
                chat_id=self.settings['TELEGRAM_CHAT_ID']
            )
            
            self.analyzer = FuturesAnalyzer(
                client=self.client,
                user_login="Anhbaza",
                settings=self.settings
            )
            
            # Start services
            await self.notifier.start()

            start_msg = (
                "🚀 <b>Bot Trading đã khởi động</b>\n\n"
                f"⏰ Thời gian: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"👤 User: Anhbaza\n"
                f"📊 Đang theo dõi: {len(self.analyzer.WATCHED_PAIRS)} cặp tiền\n"
                f"🌍 Environment: {self.settings['ENVIRONMENT']}\n"
                "📈 Chiến lược: RSI + Volume + Price Action"
            )
            
            await self.notifier.send_message(start_msg)

         except Exception as e:
            self.logger.error(f"Error during startup: {str(e)}")
            raise
    async def shutdown(self):
        """Cleanup and shutdown"""
        if self._cleanup_done:
            return

        self._cleanup_done = True
        self._is_running = False
        
        try:
            if self.notifier:
                shutdown_msg = "⚠️ Bot đang dừng hoạt động..."
                await self.notifier.send_message(shutdown_msg)
                await self.notifier.stop()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")

    async def run(self):
        """Main bot loop"""
        try:
            while self._is_running:
                try:
                    for symbol in self.analyzer.WATCHED_PAIRS:
                        if not self._is_running:
                            break
                            
                        self.logger.info(f"Analyzing {symbol}...")
                        if await self.analyzer.quick_pre_filter(symbol):
                            signal = await self.analyzer.analyze_entry_conditions(symbol)
                            
                            if signal:
                                self.logger.info(f"Signal found for {symbol}")
                                await self.notifier.send_signal(signal)
                        
                        await asyncio.sleep(self.analyzer.RATE_LIMIT_DELAY)
                        
                    self.logger.info("Waiting 5 minutes before next scan...")
                    await asyncio.sleep(300)  # 5 minutes delay
                    
                except Exception as e:
                    self.logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(30)
                    
        except Exception as e:
            self.logger.error(f"Critical error in run loop: {str(e)}")
        finally:
            await self.shutdown()

async def main():
    """Main entry point"""
    print("\n=== BOT GIAO DỊCH BINANCE FUTURES ===")
    print(f"🕒 Thời gian: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"👤 User: Anhbaza")
    print(f"📂 Thư mục hiện tại: {os.getcwd()}")
    print("="*40 + "\n")
    
    bot = None
    
    try:
        bot = TradingBot()
        await bot.startup()
        await bot.run()
    except KeyboardInterrupt:
        print("\n⚠️ Received keyboard interrupt...")
    except Exception as e:
        print(f"\n❌ Unhandled error: {str(e)}")
    finally:
        if bot:
            await bot.shutdown()

def run_bot():
    """Run the bot with proper exception handling"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n⚠️ Stopping bot...")
    except Exception as e:
        print(f"\n❌ Unhandled error: {str(e)}")
    finally:
        try:
            loop = asyncio.get_event_loop()
            pending = asyncio.all_tasks(loop)
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()

if __name__ == "__main__":
    run_bot()