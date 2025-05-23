#!/usr/bin/env python3
"""
Bot Trading API REST - Main Entry Point
Author: Anhbaza
Last Updated: 2025-05-23 08:33:58
"""

import os
import sys
import time
import asyncio
import logging
import yaml
from datetime import datetime
from typing import Optional, Dict, List
from binance import Client

from config.logging_config import setup_logging
from config.settings import load_settings
from services.telegram_notifier import TelegramNotifier
from core.analyzer.futures import FuturesAnalyzer
from utils.order_tracker import OrderTracker
from core.models import SignalData

class TradingBot:
    def __init__(self):
        """Initialize bot instance"""
        self.logger = setup_logging()
        self.settings: Dict = {}
        self.notifier: Optional[TelegramNotifier] = None
        self.analyzer: Optional[FuturesAnalyzer] = None
        self.client: Optional[Client] = None
        self.order_tracker: Optional[OrderTracker] = None
        self._cleanup_done = False
        self._is_running = True

    def initialize(self):
        """Initialize synchronous components"""
        try:
            # Load settings
            self.logger.info("Loading configuration...")
            self.settings = load_settings()
            
            # Load additional config for order tracking
            try:
                with open('config.yaml', 'r', encoding='utf-8') as f:
                    tracking_config = yaml.safe_load(f)
            except UnicodeDecodeError:
                with open('config.yaml', 'r', encoding='latin-1') as f:
                    tracking_config = yaml.safe_load(f)
            
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
            
            # Initialize order tracker
            self.order_tracker = OrderTracker(
                telegram_token=self.settings['TELEGRAM_BOT_TOKEN'],
                chat_id=self.settings['TELEGRAM_CHAT_ID']
            )
            
            self.analyzer = FuturesAnalyzer(
                client=self.client,
                user_login="Anhbaza",
                settings=self.settings
            )
            
            return True

        except Exception as e:
            self.logger.error(f"Error during initialization: {str(e)}")
            return False

    async def start(self):
        """Start bot services"""
        try:
            # Start Telegram notifier
            await self.notifier.start()

            # Get initial market data
            exchange_info = self.client.futures_exchange_info()
            total_pairs = len([
                s['symbol'] for s in exchange_info['symbols']
                if s['symbol'].endswith('USDT') 
                and s['status'] == 'TRADING'
                and not s['symbol'].startswith('DEFI')
            ])

            start_msg = (
                "🚀 <b>Bot Trading đã khởi động</b>\n\n"
                f"⏰ Thời gian: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"👤 User: Anhbaza01\n"
                f"📊 Số cặp theo dõi: {total_pairs}\n"
                f"🌍 Environment: {self.settings['ENVIRONMENT']}\n"
                "📈 Chiến lược: RSI + Volume + Price Action\n\n"
                "⚡ Đang bắt đầu quét thị trường..."
            )
            
            await self.notifier.send_message(start_msg)
            return True

        except Exception as e:
            self.logger.error(f"Error during startup: {str(e)}")
            return False

    async def stop(self):
        """Stop bot services"""
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

    async def handle_signal(self, signal: SignalData):
        """Xử lý tín hiệu giao dịch và cập nhật theo dõi lệnh"""
        try:
            # Thêm lệnh mới vào order tracker
            await self.order_tracker.add_order(
                symbol=signal.symbol,
                entry_price=signal.entry,
                direction=signal.signal_type,
                take_profit=signal.take_profit,
                stop_loss=signal.stop_loss
            )

            # Gửi tín hiệu qua Telegram như bình thường
            await self.notifier.send_signal(signal)

        except Exception as e:
            self.logger.error(f"Error handling signal: {str(e)}")

    async def update_orders(self, symbol: str, current_price: float, signal: SignalData = None):
        """Cập nhật trạng thái các lệnh"""
        try:
            new_direction = signal.signal_type if signal else None
            await self.order_tracker.update_order(symbol, current_price, new_direction)
        except Exception as e:
            self.logger.error(f"Error updating orders: {str(e)}")

    async def run(self):
        """Main bot loop"""
        try:
            while self._is_running:
                try:
                    scan_start = time.time()
                    
                    # Lấy danh sách cặp giao dịch từ Binance
                    exchange_info = self.client.futures_exchange_info()
                    symbols = [
                        s['symbol'] for s in exchange_info['symbols']
                        if s['symbol'].endswith('USDT') 
                        and s['status'] == 'TRADING'
                        and not s['symbol'].startswith('DEFI')
                    ]
                    
                    self.logger.info(f"Found {len(symbols)} trading pairs")
                    
                    # Kết quả phân tích
                    results = {
                        'signals': [],
                        'stats': {
                            'total_processed': 0,
                            'pre_filter_failed': 0,
                            'analysis_failed': 0,
                            'signals_found': 0,
                            'errors': 0
                        }
                    }

                    # Xử lý theo nhóm để tránh rate limit
                    chunk_size = 10
                    chunks = [symbols[i:i + chunk_size] for i in range(0, len(symbols), chunk_size)]
                    
                    for chunk_idx, chunk in enumerate(chunks, 1):
                        if not self._is_running:
                            break
                            
                        chunk_start = time.time()
                        self.logger.info(f"Processing chunk {chunk_idx}/{len(chunks)} ({len(chunk)} symbols)")
                        
                        for symbol in chunk:
                            try:
                                self.logger.info(f"Analyzing {symbol}...")
                                
                                # Pre-filter check
                                if not self.analyzer.quick_pre_filter(symbol):
                                    results['stats']['pre_filter_failed'] += 1
                                    continue
                                    
                                # Analyze entry conditions
                                signal = await self.analyzer.analyze_entry_conditions(symbol)
                                results['stats']['total_processed'] += 1
                                
                                if signal:
                                    results['signals'].append(signal)
                                    results['stats']['signals_found'] += 1
                                    # Sử dụng hàm handle_signal mới
                                    await self.handle_signal(signal)
                                else:
                                    results['stats']['analysis_failed'] += 1
                                
                                # Cập nhật trạng thái các lệnh hiện tại
                                current_price = float(self.client.futures_symbol_ticker(symbol=symbol)['price'])
                                await self.update_orders(symbol, current_price, signal)
                                    
                            except Exception as e:
                                self.logger.error(f"Error processing {symbol}: {str(e)}")
                                results['stats']['errors'] += 1
                                
                            # Rate limiting delay
                            await asyncio.sleep(self.analyzer.RATE_LIMIT_DELAY)
                        
                        # Log chunk completion
                        chunk_time = time.time() - chunk_start
                        self.logger.info(
                            f"Chunk {chunk_idx} completed in {chunk_time:.1f}s - "
                            f"Processed: {results['stats']['total_processed']}/{len(symbols)}"
                        )
                        
                        if chunk_time < 1:
                            await asyncio.sleep(1 - chunk_time)
                    
                    # Tính thời gian quét
                    scan_duration = time.time() - scan_start
                    
                    # Gửi báo cáo hoàn thành
                    completion_msg = (
                        f"📊 <b>HOÀN THÀNH QUÉT</b>\n\n"
                        f"Số cặp đã quét: {len(symbols)}\n"
                        f"Thời gian quét: {scan_duration:.1f}s\n"
                        f"Tín hiệu mới: {results['stats']['signals_found']}\n\n"
                        f"Chi tiết:\n"
                        f"• Fail pre-filter: {results['stats']['pre_filter_failed']}\n"
                        f"• Fail analysis: {results['stats']['analysis_failed']}\n"
                        f"• Total processed: {results['stats']['total_processed']}\n"
                        f"• Errors: {results['stats']['errors']}\n\n"
                        f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    )
                    
                    self.logger.info(completion_msg)
                    await self.notifier.send_message(completion_msg)
                    
                    # Đợi trước khi quét tiếp
                    self.logger.info("Waiting 5 minutes before next scan...")
                    await asyncio.sleep(300)  # 5 phút
                        
                except Exception as e:
                    self.logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(30)
                        
        except Exception as e:
            self.logger.error(f"Critical error in run loop: {str(e)}")
        finally:
            await self.stop()

async def main():
    """Main entry point"""
    print("\n=== BOT GIAO DỊCH BINANCE FUTURES ===")
    print(f"🕒 Thời gian: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"👤 User: Anhbaza01")
    print(f"📂 Thư mục hiện tại: {os.getcwd()}")
    print("="*40 + "\n")
    
    bot = None
    
    try:
        bot = TradingBot()
        if not bot.initialize():
            print("\n❌ Initialization failed. Check the logs for details.")
            return
            
        if not await bot.start():
            print("\n❌ Startup failed. Check the logs for details.")
            return
            
        await bot.run()
        
    except KeyboardInterrupt:
        print("\n⚠️ Received keyboard interrupt...")
    except Exception as e:
        print(f"\n❌ Unhandled error: {str(e)}")
    finally:
        if bot:
            await bot.stop()

def run_bot():
    """Run the bot with proper exception handling"""
    try:
        if os.name == 'nt':  # Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
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
            input("\nPress Enter to exit...")

if __name__ == "__main__":
    run_bot()