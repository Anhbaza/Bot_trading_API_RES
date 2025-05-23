#!/usr/bin/env python3
"""
Order Management Bot - Entry Point
Author: Anhbaza01
Last Updated: 2025-05-23 12:12:47 UTC
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
import yaml
from decimal import Decimal
import json
import tkinter as tk
from typing import Dict, Any, Optional, Callable

from shared.constants import (
    MSG_TYPE_SIGNAL, MSG_TYPE_ORDER_CONFIRM,
    MSG_TYPE_ORDER_UPDATE, MSG_TYPE_ORDER_CLOSE,
    ORDER_BOT_NAME,
    TELEGRAM_POOL_SIZE,
    TELEGRAM_CONNECTION_TIMEOUT,
    TELEGRAM_READ_TIMEOUT,
    TELEGRAM_WRITE_TIMEOUT,
    TELEGRAM_CONNECT_TIMEOUT
)
from shared.telegram_service import TelegramService
from order_management.models.order_data import OrderData
from order_management.services.order_manager import OrderManager
from order_management.gui.order_window import OrderWindow
from order_management.services.telegram_handler import TelegramHandler

class OrderBot:
    def __init__(self):
        """Initialize order bot"""
        self.logger = self._setup_logging()
        self.manager = OrderManager()
        self.telegram = None
        self.telegram_handler = None
        self.gui = None
        self._is_running = True
        print("\n[DEBUG] OrderBot initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            format='%(asctime)s UTC | %(levelname)s | %(message)s',
            level=logging.INFO,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        return logging.getLogger("OrderBot")

    def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            print("\n[DEBUG] Loading config...")
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            self.telegram = TelegramService(
                token=config['telegram']['token'],
                chat_id=config['telegram']['chat_id'],
                bot_name=ORDER_BOT_NAME
            )

            self.telegram_handler = TelegramHandler(
                token=config['telegram']['token'],
                chat_id=config['telegram']['chat_id'],
                order_manager=self.manager,
                on_signal_received=self._on_signal_received,
                on_order_update=self._on_order_update
            )
            
            print("\n[DEBUG] Config loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            print(f"\n[DEBUG] Config load error: {str(e)}")
            return False

    def _on_signal_received(self, signal_data: dict):
        """Handle new signal from trading bot"""
        try:
            print(f"\n[DEBUG] Signal received in bot: {signal_data}")
            
            if self.gui:
                print("\n[DEBUG] Updating GUI with signal...")
                symbol = signal_data['symbol']
                self.gui.update_signals({symbol: signal_data})
                print(f"\n[DEBUG] GUI updated for {symbol}")
            else:
                print("\n[DEBUG] WARNING: GUI not initialized!")
                
        except Exception as e:
            print(f"\n[DEBUG] Error in _on_signal_received: {str(e)}")
            self.logger.error(f"Error handling signal: {str(e)}")

    def _on_order_update(self, symbol: str, current_price: Decimal):
        """Handle order update"""
        try:
            if self.gui:
                self.gui.update_orders(
                    self.manager.active_orders,
                    {
                        "total_profit": float(self.manager.total_profit),
                        "win_rate": self.manager.get_statistics()["win_rate"]
                    }
                )
        except Exception as e:
            self.logger.error(f"Error updating orders: {str(e)}")

    def _on_signal_confirm(self, symbols: list[str]):
        """Handle signal confirmation from GUI"""
        asyncio.create_task(self.telegram_handler.send_order_confirmation(symbols))

    async def _delete_webhook(self):
        """Delete any active webhook"""
        try:
            print("\n[DEBUG] Deleting webhook...")
            await self.telegram.bot.delete_webhook(drop_pending_updates=True)
            print("\n[DEBUG] Webhook deleted successfully")
            self.logger.info("Successfully deleted webhook")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting webhook: {str(e)}")
            print(f"\n[DEBUG] Webhook deletion error: {str(e)}")
            return False

    async def _process_telegram_updates(self):
     """Process Telegram updates"""
     offset = 0
     print("\n[DEBUG] Starting Telegram update processing...")
    
     while self._is_running:
        try:
            # Get updates with offset
            updates = await self.telegram.bot.get_updates(
                offset=offset,
                timeout=30,
                allowed_updates=['message']
            )
            
            print(f"\n[DEBUG] Received {len(updates)} updates")
            
            for update in updates:
                # Update offset
                offset = update.update_id + 1
                
                if update.message and update.message.text:
                    print(f"\n[DEBUG] Processing update {update.update_id}")
                    print(f"\n[DEBUG] Message text: {update.message.text}")
                    
                    # Handle message
                    await self.telegram_handler.handle_message(update.message.text)
            
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"\n[DEBUG] Update processing error: {str(e)}")
            await asyncio.sleep(5)

    async def start(self):
        """Start the bot"""
        try:
            print("\n=== BOT QUẢN LÝ LỆNH GIAO DỊCH ===")
            print(f"🕒 Thời gian: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"👤 User: Anhbaza01")
            print(f"📂 Thư mục hiện tại: {os.getcwd()}")
            print("="*40 + "\n")

            # Initialize components
            if not self.load_config():
                print("\n❌ Khởi tạo thất bại. Kiểm tra logs.")
                return

            # Delete webhook before starting
            if not await self._delete_webhook():
                print("\n❌ Không thể xóa webhook. Kiểm tra logs.")
                return

            # Initialize GUI first
            print("\n[DEBUG] Initializing GUI...")
            self.gui = OrderWindow(
                on_signal_confirm=self._on_signal_confirm
            )
            print("\n[DEBUG] GUI initialized")
            
            # Start Telegram update task
            print("\n[DEBUG] Starting Telegram handler...")
            asyncio.create_task(self._process_telegram_updates())
            print("\n[DEBUG] Telegram handler started")
            
            # Send startup notification
            await self.telegram.send_message(
                "🚀 Bot Quản lý Lệnh đã khởi động\n"
                f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"👤 User: Anhbaza01"
            )
            
            # Run GUI (this will block)
            print("\n[DEBUG] Starting GUI main loop...")
            self.gui.run()

        except Exception as e:
            self.logger.error(f"Error starting bot: {str(e)}")
            print(f"\n[DEBUG] Startup error: {str(e)}")
        finally:
            self._is_running = False
            await self.telegram.send_message("⚠️ Bot Quản lý Lệnh đã dừng")

    async def stop(self):
        """Stop the bot"""
        self._is_running = False
        if self.gui:
            self.gui.window.quit()

def main():
    """Main entry point"""
    try:
        print("\n=== Starting Order Management Bot ===")
        
        # Create and start bot
        bot = OrderBot()
        
        # Set event loop policy for Windows
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run bot
        print("\n[DEBUG] Starting bot...")
        loop.run_until_complete(bot.start())
        
    except KeyboardInterrupt:
        print("\n⚠️ Đang dừng bot...")
    except Exception as e:
        print(f"\n❌ Lỗi không xử lý được: {str(e)}")
    finally:
        try:
            loop = asyncio.get_event_loop()
            
            # Cancel all tasks
            tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            if tasks:
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            
            # Shutdown async generators
            loop.run_until_complete(loop.shutdown_asyncgens())
            
        finally:
            loop.close()
            
        # Wait for user input before exit on Windows
        if os.name == 'nt':
            input("\nNhấn Enter để thoát...")

if __name__ == "__main__":
    main()