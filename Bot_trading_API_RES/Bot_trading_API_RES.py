#!/usr/bin/env python3
"""
Binance Futures Trading Bot with API REST
Author: Anhbaza01
Last Updated: 2025-05-23 16:07:17 UTC
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
import json
import yaml
from typing import Dict, Any, List, Optional
from decimal import Decimal

from binance.client import Client  # Changed from AsyncClient to Client
from binance.exceptions import BinanceAPIException

from shared.telegram_service import TelegramService
from shared.constants import (
    MSG_TYPE_SIGNAL,
    TRADING_BOT_NAME,
    MIN_VOLUME_USDT,
    MAX_TRADES_PER_SYMBOL,
    RSI_PERIOD,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD
)

class TradingBot:
    def __init__(self):
        """Initialize trading bot"""
        self.logger = self._setup_logging()
        self.client = None
        self.telegram = None
        self._is_running = True
        self.trading_pairs = []
        self.analysis_data = {}
        print("\n[DEBUG] TradingBot initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        # Create logs directory if not exists
        os.makedirs('logs', exist_ok=True)
        
        # Setup logging
        log_filename = f'logs/bot_trading_{datetime.utcnow().strftime("%Y%m%d")}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s UTC | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler(sys.stdout)
            ],
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        logger = logging.getLogger(TRADING_BOT_NAME)
        
        # Log startup information
        logger.info("="*50)
        logger.info(f"Bot Trading API REST - Logging Initialized")
        logger.info(f"Log Level: {logging.getLevelName(logger.getEffectiveLevel())}")
        logger.info(f"Log File: {log_filename}")
        logger.info(f"Current Time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"User: {os.getlogin()}")
        logger.info("="*50)
        
        return logger

    async def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            self.logger.info("Loading configuration...")
            
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Initialize Binance client
            self.client = Client(
                api_key=config['binance']['api_key'],
                api_secret=config['binance']['api_secret']
            )
            
            # Test connection
            self.client.ping()
            self.logger.info("Successfully connected to Binance API")

            # Initialize Telegram service
            self.logger.info("Starting Telegram notification service...")
            self.telegram = TelegramService(
                token=config['telegram']['token'],
                chat_id=config['telegram']['chat_id'],
                bot_name=TRADING_BOT_NAME
            )
            
            await self.telegram.test_connection()
            self.logger.info("Telegram notification service started successfully")
            
            # Send startup notification
            await self.telegram.send_message(
                "🚀 Bot Giao dịch đã khởi động\n"
                f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"👤 User: {os.getlogin()}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            return False

    def get_trading_pairs(self) -> List[str]:
        """Get list of trading pairs"""
        try:
            # Get exchange info
            exchange_info = self.client.futures_exchange_info()
            
            # Filter trading pairs
            pairs = []
            for symbol in exchange_info['symbols']:
                if symbol['status'] == 'TRADING' and symbol['quoteAsset'] == 'USDT':
                    pairs.append(symbol['symbol'])
            
            self.logger.info(f"Found {len(pairs)} trading pairs")
            return pairs

        except Exception as e:
            self.logger.error(f"Error getting trading pairs: {str(e)}")
            return []

    async def send_signal(self, signal_data: Dict[str, Any]):
        """Send trading signal"""
        try:
            # Format command message
            command = {
                "type": MSG_TYPE_SIGNAL,
                "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                "data": {
                    "symbol": signal_data["symbol"],
                    "signal_type": signal_data["signal_type"],
                    "entry": str(signal_data["entry"]),
                    "take_profit": str(signal_data["take_profit"]),
                    "stop_loss": str(signal_data["stop_loss"]),
                    "confidence": signal_data.get("confidence", 0.55),
                    "reason": signal_data.get("reason", "")
                }
            }
            
            # Convert to JSON string
            message = f"CMD:{json.dumps(command)}"
            
            # Debug log
            print(f"\n[DEBUG] Sending signal: {message}")
            
            # Send via Telegram
            await self.telegram.send_message(message)
            print(f"\n[DEBUG] Signal sent for {signal_data['symbol']}")

        except Exception as e:
            print(f"\n[DEBUG] Error sending signal: {str(e)}")
            self.logger.error(f"Error sending signal: {str(e)}")

    def get_klines(self, symbol: str, interval: str = '5m', limit: int = 100) -> List[Dict[str, Any]]:
        """Get kline/candlestick data"""
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            formatted_klines = []
            for k in klines:
                formatted_klines.append({
                    'timestamp': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })
                
            return formatted_klines

        except Exception as e:
            self.logger.error(f"Error getting klines for {symbol}: {str(e)}")
            return []

    def calculate_indicators(self, klines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate technical indicators"""
        try:
            if not klines:
                return {}

            # Calculate RSI
            closes = [k['close'] for k in klines]
            gains = []
            losses = []
            
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                if change >= 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))

            # Calculate average gains and losses
            avg_gain = sum(gains[-RSI_PERIOD:]) / RSI_PERIOD
            avg_loss = sum(losses[-RSI_PERIOD:]) / RSI_PERIOD

            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            # Calculate Volume Ratio
            volume_ratio = klines[-1]['volume'] / sum(k['volume'] for k in klines[-20:]) * 20

            return {
                'rsi': rsi,
                'volume_ratio': volume_ratio
            }

        except Exception as e:
            self.logger.error(f"Error calculating indicators: {str(e)}")
            return {}

    def analyze_symbol(self, symbol: str, klines: List[Dict[str, Any]], indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze symbol for trading signals"""
        try:
            if not klines or not indicators:
                return None

            rsi = indicators['rsi']
            volume_ratio = indicators['volume_ratio']
            current_price = klines[-1]['close']

            # Check conditions for signals
            signal = None
            
            # LONG signal conditions
            if (rsi < RSI_OVERSOLD and volume_ratio > 1.15):
                signal = {
                    'symbol': symbol,
                    'signal_type': 'LONG',
                    'entry': current_price,
                    'take_profit': current_price * 1.02,  # 2% profit target
                    'stop_loss': current_price * 0.99,    # 1% stop loss
                    'confidence': 0.55,
                    'reason': f"RSI({RSI_PERIOD}/15m): {rsi:.1f}/{RSI_OVERSOLD}\nVolume Ratio: {volume_ratio:.2f}"
                }
                
            # SHORT signal conditions
            elif (rsi > RSI_OVERBOUGHT and volume_ratio > 1.15):
                signal = {
                    'symbol': symbol,
                    'signal_type': 'SHORT',
                    'entry': current_price,
                    'take_profit': current_price * 0.98,  # 2% profit target
                    'stop_loss': current_price * 1.01,    # 1% stop loss
                    'confidence': 0.55,
                    'reason': f"RSI({RSI_PERIOD}/15m): {rsi:.1f}/{RSI_OVERBOUGHT}\nVolume Ratio: {volume_ratio:.2f}"
                }

            return signal

        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {str(e)}")
            return None

    async def process_symbol(self, symbol: str):
        """Process single symbol"""
        try:
            # Get klines data
            klines = self.get_klines(symbol)  # Removed await
            if not klines:
                return

            # Calculate indicators
            indicators = self.calculate_indicators(klines)
            if not indicators:
                return

            # Analyze for signals
            signal = self.analyze_symbol(symbol, klines, indicators)
            if signal:
                # Send signal
                await self.send_signal(signal)
                self.logger.info(f"Signal found for {symbol}: {signal['signal_type']}")

        except Exception as e:
            self.logger.error(f"Error processing {symbol}: {str(e)}")

    async def run(self):
        """Main bot loop"""
        try:
            print("\n=== BOT GIAO DỊCH BINANCE FUTURES ===")
            print(f"🕒 Thời gian: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"👤 User: {os.getlogin()}")
            print(f"📂 Thư mục hiện tại: {os.getcwd()}")
            print("="*40 + "\n")

            # Initialize
            if not await self.load_config():
                self.logger.error("Failed to initialize. Check logs.")
                return

            while self._is_running:
                try:
                    # Get trading pairs
                    self.trading_pairs = self.get_trading_pairs()  # Removed await
                    if not self.trading_pairs:
                        await asyncio.sleep(60)
                        continue

                    # Process symbols in chunks
                    chunk_size = 10
                    for i in range(0, len(self.trading_pairs), chunk_size):
                        chunk = self.trading_pairs[i:i + chunk_size]
                        self.logger.info(f"Processing chunk {i//chunk_size + 1}/{(len(self.trading_pairs)-1)//chunk_size + 1} ({len(chunk)} symbols)")
                        
                        for symbol in chunk:
                            self.logger.info(f"Analyzing {symbol}...")
                            await self.process_symbol(symbol)
                            await asyncio.sleep(1)  # Rate limiting

                        await asyncio.sleep(2)  # Delay between chunks

                    # Delay between full scans
                    await asyncio.sleep(300)  # 5 minutes

                except Exception as e:
                    self.logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(60)

        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Fatal error: {str(e)}")
        finally:
            self._is_running = False
            self.logger.info("Bot stopped")

def main():
    """Main entry point"""
    try:
        # Create and start bot
        bot = TradingBot()
        
        # Set event loop policy for Windows
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run bot
        loop.run_until_complete(bot.run())
        
    except KeyboardInterrupt:
        print("\n⚠️ Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
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
    main()