#!/usr/bin/env python3
"""
Bot Trading API REST - Main Entry Point
Author: Anhbaza
Date: 2025-05-22
"""

import os
import asyncio
import logging
from datetime import datetime

from config.settings import setup_environment
from config.logging_config import setup_logging
from core.analyzer.futures import FuturesAnalyzer
from services.binance_client import BinanceClient
from services.telegram_notifier import TelegramNotifier

async def main():
    """Main entry point for the trading bot"""
    try:
        # Print startup info
        print("\n=== BOT GIAO DỊCH BINANCE FUTURES ===")
        print(f"🕒 Thời gian: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"👤 User: Anhbaza")
        print(f"📂 Thư mục hiện tại: {os.getcwd()}")
        print("="*40 + "\n")
        
        # Setup
        logger = setup_logging()
        if not setup_environment():
            raise ValueError("Failed to setup environment")
            
        # Initialize components
        client = BinanceClient()
        await client.initialize_async_client()
        
        analyzer = FuturesAnalyzer(client, user_login="Anhbaza")
        notifier = TelegramNotifier()
        await notifier.start()
        
        # Send startup notification
        start_msg = (
            "🚀 Bot đã khởi động\n"
            f"Thời gian: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"Version: 1.0.0"
        )
        logger.info(start_msg)
        await notifier.send_message(start_msg)
        
        while True:  # Main loop
            try:
                # Get trading pairs
                symbols = await client.get_futures_symbols()
                logger.info(f"Đã tải {len(symbols)} cặp giao dịch hợp lệ")
                
                # Process symbols
                for symbol in symbols:
                    try:
                        # Quick pre-filter
                        if not await analyzer.quick_pre_filter(symbol):
                            continue
                            
                        # Analyze entry conditions
                        signal = await analyzer.analyze_entry_conditions(symbol)
                        
                        if signal:
                            # Send signal notification
                            await notifier.send_signal(signal)
                            
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {str(e)}")
                        
                    # Rate limiting
                    await asyncio.sleep(analyzer.RATE_LIMIT_DELAY)
                    
                # Wait before next scan
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                await asyncio.sleep(30)
                
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        
    finally:
        # Cleanup
        await notifier.stop()
        await client.close_async_client()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Stopping bot...")
    except Exception as e:
        print(f"\n❌ Unhandled error: {str(e)}")
