#!/usr/bin/env python3
"""
Order Management Bot - Entry Point
Author: Anhbaza01
Last Updated: 2025-05-23 11:35:10
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
import yaml
from decimal import Decimal

from shared.constants import (
    MSG_TYPE_SIGNAL, MSG_TYPE_ORDER_CONFIRM,
    MSG_TYPE_ORDER_UPDATE, MSG_TYPE_ORDER_CLOSE,
    ORDER_BOT_NAME
)
from shared.telegram_service import TelegramService
from order_management.models.order_data import OrderData
from order_management.services.order_manager import OrderManager
from order_management.gui.order_window import OrderWindow
from order_management.services.telegram_handler import TelegramHandler

class OrderBot:
    def __init__(self):
        self.logger = self._setup_logging()
        self.manager = OrderManager()
        self.telegram = None
        self.telegram_handler = None
        self.gui = None
        self._is_running = True
    async def _delete_webhook(self):
        """Delete any active webhook"""
        try:
            await self.telegram.bot.delete_webhook(drop_pending_updates=True)
            self.logger.info("Successfully deleted webhook")
        except Exception as e:
            self.logger.error(f"Error deleting webhook: {str(e)}")
            return False
        return True
    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logging.basicConfig(
            format='%(asctime)s UTC | %(levelname)s | %(message)s',
            level=logging.INFO,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        return logging.getLogger("OrderBot")

    def load_config(self) -> bool:
        """Load configuration"""
        try:
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
            
            return True
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            return False

    def _on_signal_received(self, signal_data: dict):
        """Handle new signal from trading bot"""
        try:
            self.logger.info(f"Received signal in GUI: {signal_data}")
            
            if self.gui:
                # Update signals dictionary with new signal
                symbol = signal_data['symbol']
                self.gui.update_signals({symbol: signal_data})
                self.logger.info(f"Updated GUI with signal for {symbol}")
            else:
                self.logger.warning("GUI not initialized")
                
        except Exception as e:
            self.logger.error(f"Error updating GUI with signal: {str(e)}")

    def _on_order_update(self, symbol: str, current_price: Decimal):
        """Handle order update"""
        if self.gui:
            self.gui.update_orders(
                self.manager.active_orders,
                {
                    "total_profit": float(self.manager.total_profit),
                    "win_rate": self.manager.win_rate
                }
            )

    def _on_signal_confirm(self, symbols: list[str]):
        """Handle signal confirmation from GUI"""
        asyncio.create_task(self.telegram_handler.send_order_confirmation(symbols))

    async def _process_telegram_updates(self):
        """Process Telegram updates"""
        offset = 0
        while self._is_running:
            try:
                # Get updates with offset
                updates = await self.telegram.bot.get_updates(
                    offset=offset,
                    timeout=30,
                    allowed_updates=['message']
                )
                
                for update in updates:
                    # Update offset
                    offset = update.update_id + 1
                    
                    if update.message and update.message.text:
                        # Log received message
                        self.logger.info(f"Received message: {update.message.text}")
                        
                        # Handle message
                        await self.telegram_handler.handle_message(update.message.text)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error processing updates: {str(e)}")
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

            # Start Telegram update task
            asyncio.create_task(self._process_telegram_updates())

            # Initialize and start GUI
            self.gui = OrderWindow(
                on_signal_confirm=self._on_signal_confirm
            )
            
            # Send startup notification
            await self.telegram.send_message(
                "🚀 Bot Quản lý Lệnh đã khởi động\n"
                f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"👤 User: Anhbaza01"
            )
            
            # Run GUI (this will block)
            self.gui.run()

        except Exception as e:
            self.logger.error(f"Error starting bot: {str(e)}")
        finally:
            self._is_running = False
            await self.telegram.send_message("⚠️ Bot Quản lý Lệnh đã dừng")


def main():
    """Main entry point"""
    bot = OrderBot()
    
    try:
        if os.name == 'nt':  # Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
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
