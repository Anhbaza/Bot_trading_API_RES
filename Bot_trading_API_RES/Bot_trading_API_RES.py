#!/usr/bin/env python3
"""
Trading Bot
Author: Anhbaza01
Version: 1.0.0
Last Updated: 2025-05-23 19:19:10 UTC
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
import json
import yaml
import aiohttp
from typing import Dict, Any, List, Optional
from binance.client import Client
from binance.exceptions import BinanceAPIException

from shared.constants import *
from shared.telegram_service import TelegramService
from shared.signal_processor import SignalProcessor

class TradingBot:
    def __init__(self):
        """Initialize trading bot"""
        self.logger = self._setup_logging()
        self.telegram = None
        self._is_running = True
        self.monitored_pairs = []  # All valid pairs
        self.watched_pairs = []    # Specifically watched pairs
        self.active_signals = {}
        self.client = None
        self.signal_processor = None
        self.scanning_mode = SCAN_MODE_ALL
        self.user = "Anhbaza01"
        
        self.logger.info(f"Bot initialized at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        self.logger.info(f"User: {self.user}")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            logs_dir = os.path.join(current_dir, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            log_filename = os.path.join(
                logs_dir, 
                f'trading_bot_{datetime.utcnow().strftime("%Y%m%d")}.log'
            )
            
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
            
            logger.info("="*50)
            logger.info("Trading Bot - Logging Initialized")
            logger.info(f"Log Level: {logging.getLevelName(logger.getEffectiveLevel())}")
            logger.info(f"Log File: {log_filename}")
            logger.info(f"Current Time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"User: {self.user}")
            logger.info("="*50)
            
            return logger
            
        except Exception as e:
            print(f"Error setting up logging: {str(e)}")
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s UTC | %(levelname)s | %(message)s',
                handlers=[logging.StreamHandler(sys.stdout)],
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            return logging.getLogger(TRADING_BOT_NAME)

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'config.yaml')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ValueError("Empty configuration file")
                
            required_keys = ['telegram', 'trading']
            missing_keys = [key for key in required_keys if key not in config]
            
            if missing_keys:
                raise ValueError(f"Missing required config keys: {', '.join(missing_keys)}")
                
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {str(e)}")
            return {}

    def setup_binance(self) -> bool:
        """Setup Binance API client"""
        try:
            self.logger.info("Connecting to Binance...")
            self.client = Client()
            self.client.ping()
            self.logger.info("Connected to Binance API")
            return True
            
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Binance setup error: {str(e)}")
            return False

    async def setup_telegram(self, config: Dict[str, Any]) -> bool:
        """Setup Telegram notification service"""
        try:
            if not config.get('telegram'):
                raise ValueError("Telegram configuration missing")
                
            self.telegram = TelegramService(
                token=config['telegram']['token'],
                chat_id=config['telegram']['chat_id']
            )
            
            if await self.telegram.test_connection():
                # Send startup message
                await self.telegram.send_startup_message(self.user)
                return True
            else:
                raise ConnectionError("Failed to connect to Telegram")
            
        except Exception as e:
            self.logger.error(f"Telegram setup error: {str(e)}")
            return False

    async def get_trading_pairs(self) -> List[str]:
        """Get list of valid trading pairs"""
        try:
            valid_pairs = []
            
            # Get exchange info
            exchange_info = self.client.futures_exchange_info()
            
            # Get futures ticker data
            async with aiohttp.ClientSession() as session:
                async with session.get('https://fapi.binance.com/fapi/v1/ticker/24hr') as response:
                    if response.status != 200:
                        raise ConnectionError("Failed to get ticker data")
                    tickers = await response.json()
            
            # Calculate USDT volume
            volume_dict = {
                t['symbol']: float(t['volume']) * float(t['lastPrice']) 
                for t in tickers if t['symbol'].endswith('USDT')
            }
            
            # Filter valid pairs
            for symbol in exchange_info['symbols']:
                if (symbol['status'] == 'TRADING' and
                    symbol['quoteAsset'] == 'USDT' and
                    symbol['contractType'] == 'PERPETUAL' and
                    volume_dict.get(symbol['symbol'], 0) >= MIN_VOLUME_USDT):
                    valid_pairs.append(symbol['symbol'])
            
            # Log information
            self.logger.info(f"Found {len(valid_pairs)} valid pairs")
            
            # Sort and show top pairs by volume
            top_pairs = sorted(
                [(p, volume_dict[p]) for p in valid_pairs],
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            self.logger.info("Top 5 pairs by volume:")
            for pair, volume in top_pairs:
                self.logger.info(f"  {pair}: ${volume:,.2f}")
            
            return valid_pairs
            
        except Exception as e:
            self.logger.error(f"Error getting trading pairs: {str(e)}")
            return []

    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100) -> List[Dict]:
        """Get klines/candlestick data"""
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            return [{
                'timestamp': k[0],
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5]),
                'close_time': k[6],
                'quote_volume': float(k[7]),
                'trades': int(k[8]),
                'taker_buy_base': float(k[9]),
                'taker_buy_quote': float(k[10])
            } for k in klines]
            
        except Exception as e:
            self.logger.error(f"Error getting klines for {symbol}: {str(e)}")
            return []

    async def process_signal(self, symbol: str, klines: List[Dict]) -> Optional[Dict]:
     """Process and generate trading signal"""
     try:
        # Log start of processing
        self.logger.info(f"Processing signal for {symbol}...")

        # Check data validity
        if not klines:
            self.logger.info(f"{symbol}: No kline data available")
            return None
            
        if len(klines) < 50:
            self.logger.info(f"{symbol}: Insufficient kline data (need 50, got {len(klines)})")
            return None
            
        # Calculate RSI
        closes = [k['close'] for k in klines]
        rsi = self.signal_processor._calculate_rsi(closes)
        
        if rsi is None:
            self.logger.info(f"{symbol}: Failed to calculate RSI")
            return None
            
        # Log RSI value
        self.logger.info(f"{symbol}: Current RSI = {rsi:.2f}")
        
        # Check RSI conditions
        signal_type = None
        if rsi <= RSI_OVERSOLD:
            self.logger.info(f"{symbol}: RSI Oversold condition met (RSI <= {RSI_OVERSOLD})")
            # Check volume for LONG signal
            volume_signal = self.signal_processor.check_volume_signal(klines)
            if volume_signal == "LONG":
                self.logger.info(f"{symbol}: Volume breakout confirmed for LONG")
                signal_type = "LONG"
            else:
                self.logger.info(f"{symbol}: No volume confirmation for LONG")
                
        elif rsi >= RSI_OVERBOUGHT:
            self.logger.info(f"{symbol}: RSI Overbought condition met (RSI >= {RSI_OVERBOUGHT})")
            # Check volume for SHORT signal
            volume_signal = self.signal_processor.check_volume_signal(klines)
            if volume_signal == "SHORT":
                self.logger.info(f"{symbol}: Volume breakout confirmed for SHORT")
                signal_type = "SHORT"
            else:
                self.logger.info(f"{symbol}: No volume confirmation for SHORT")
        else:
            self.logger.info(f"{symbol}: RSI between {RSI_OVERSOLD} and {RSI_OVERBOUGHT}, no signal")
                
        if signal_type:
            current_price = klines[-1]['close']
            self.logger.info(f"{symbol}: Calculating targets for {signal_type} at {current_price}")
            
            targets = self.calculate_targets(symbol, signal_type, current_price)
            
            if targets['tp'] and targets['sl']:
                signal = {
                    'id': f"{symbol}_{datetime.utcnow().timestamp()}",
                    'symbol': symbol,
                    'type': signal_type,
                    'entry': current_price,
                    'tp': targets['tp'],
                    'sl': targets['sl'],
                    'time': datetime.utcnow(),
                    'rsi': rsi
                }
                
                # Calculate and log confidence score
                signal['confidence'] = self.signal_processor.calculate_confidence(
                    signal, klines
                )
                self.logger.info(
                    f"{symbol}: Signal confidence = {signal['confidence']}% "
                    f"(threshold: {CONFIDENCE_THRESHOLD}%)"
                )
                
                # Check confidence threshold
                if signal['confidence'] >= CONFIDENCE_THRESHOLD:
                    self.logger.info(
                        f"{symbol}: Valid signal found - "
                        f"{signal_type} @ {current_price} "
                        f"(TP: {targets['tp']}, SL: {targets['sl']})"
                    )
                    return signal
                else:
                    self.logger.info(
                        f"{symbol}: Signal rejected - "
                        f"Confidence {signal['confidence']}% below threshold"
                    )
            else:
                self.logger.info(f"{symbol}: Failed to calculate valid TP/SL levels")
        
        return None
        
     except Exception as e:
        self.logger.error(f"Error processing signal for {symbol}: {str(e)}")
        return None

    async def check_signals(self):
        """Check for trading signals"""
        try:
            pairs_to_check = (
                self.watched_pairs if self.scanning_mode == SCAN_MODE_WATCHED
                else self.monitored_pairs
            )
            
            for symbol in pairs_to_check:
                # Update existing signals first
                existing_signals = [s for s in self.active_signals.values() 
                                  if s['symbol'] == symbol]
                
                for signal in existing_signals:
                    klines = self.get_klines(symbol)
                    if not klines:
                        continue
                        
                    # Check trend changes
                    trend_analysis = self.signal_processor.analyze_trend(signal, klines)
                    
                    if trend_analysis['trend_changed']:
                        await self.close_signal(
                            signal['id'],
                            "TREND_CHANGE",
                            klines[-1]['close']
                        )
                    elif trend_analysis['trend_reinforced']:
                        # Update targets
                        signal.update(trend_analysis['new_targets'])
                        await self.send_signal_update(signal)
                
                # Look for new signals if capacity allows
                if len(existing_signals) >= MAX_TRADES_PER_SYMBOL:
                    continue
                    
                # Get fresh data for new signal check
                klines = self.get_klines(symbol)
                if not klines:
                    continue
                    
                # Process new signal
                new_signal = await self.process_signal(symbol, klines)
                if new_signal:
                    self.active_signals[new_signal['id']] = new_signal
                    await self.send_new_signal(new_signal)
                    
        except Exception as e:
            self.logger.error(f"Error checking signals: {str(e)}")

    async def send_new_signal(self, signal: Dict[str, Any]):
        """Send new signal notification"""
        try:
            # Format message
            message = self.signal_processor.format_signal_message(
                signal, "NEW"
            )
            
            # Send to Telegram
            await self.telegram.send_message(message)
            
            # Send to Manager Bot
            await self.send_to_manager({
                'type': MSG_TYPE_SIGNAL,
                'data': signal
            })
            
            self.logger.info(
                f"New signal sent: {signal['symbol']} {signal['type']} "
                f"(Confidence: {signal['confidence']}%)"
            )
            
        except Exception as e:
            self.logger.error(f"Error sending new signal: {str(e)}")

    async def send_signal_update(self, signal: Dict[str, Any]):
        """Send signal update notification"""
        try:
            # Format message
            message = self.signal_processor.format_signal_message(
                signal, "UPDATE"
            )
            
            # Send to Telegram
            await self.telegram.send_message(message)
            
            # Send to Manager Bot
            await self.send_to_manager({
                'type': MSG_TYPE_UPDATE,
                'data': signal
            })
            
            self.logger.info(f"Signal updated: {signal['symbol']}")
            
        except Exception as e:
            self.logger.error(f"Error sending signal update: {str(e)}")

    async def close_signal(self, signal_id: str, reason: str, close_price: float):
        """Close a signal and send notification"""
        try:
            if signal_id not in self.active_signals:
                return
                
            signal = self.active_signals[signal_id]
            signal['close_price'] = close_price
            signal['close_reason'] = reason
            
            # Format message
            message = self.signal_processor.format_signal_message(
                signal, "CLOSE"
            )
            
            # Send to Telegram
            await self.telegram.send_message(message)
            
            # Send to Manager Bot
            await self.send_to_manager({
                'type': MSG_TYPE_CLOSE,
                'data': signal
            })
            
            # Remove signal
            del self.active_signals[signal_id]
            
            self.logger.info(f"Signal closed: {signal['symbol']} ({reason})")
            
        except Exception as e:
            self.logger.error(f"Error closing signal: {str(e)}")

    async def send_to_manager(self, data: Dict[str, Any]):
        """Send data to Manager Bot"""
        try:
            # Implementation depends on your manager bot interface
            pass
        except Exception as e:
            self.logger.error(f"Error sending to manager: {str(e)}")

    async def handle_manager_request(self, request: Dict[str, Any]):
        """Handle request from Manager Bot"""
        try:
            action = request.get('action')
            
            if action == "WATCH_PAIRS":
                self.watched_pairs = request['pairs']
                self.scanning_mode = SCAN_MODE_WATCHED
                
                self.logger.info(
                    f"Now watching {len(self.watched_pairs)} pairs: "
                    f"{', '.join(self.watched_pairs)}"
                )
                
            elif action == "SCAN_ALL":
                self.watched_pairs = []
                self.scanning_mode = SCAN_MODE_ALL
                self.logger.info("Switched to scanning all pairs")
                
        except Exception as e:
            self.logger.error(f"Error handling manager request: {str(e)}")

    async def initialize(self) -> bool:
        """Initialize bot connections and settings"""
        try:
            # Load config
            config = self.load_config()
            if not config:
                return False
            
            # Setup connections
            if not self.setup_binance():
                return False
                
            if not await self.setup_telegram(config):
                return False
            
            # Initialize signal processor
            self.signal_processor = SignalProcessor(self.logger)
            
            # Get trading pairs
            self.monitored_pairs = await self.get_trading_pairs()
            if not self.monitored_pairs:
                self.logger.error("No valid trading pairs found")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization error: {str(e)}")
            return False

    async def run(self):
        """Main bot loop"""
        try:
            # Initialize
            if not await self.initialize():
                self.logger.error("Failed to initialize. Check logs.")
                return

            self.logger.info("Bot started successfully")
            self.logger.info(f"Monitoring {len(self.monitored_pairs)} pairs")
            self.logger.info(f"Current time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"User: {self.user}")

            while self._is_running:
                try:
                    loop_start = datetime.utcnow()
                    
                    # Check signals
                    await self.check_signals()
                    
                    # Calculate loop time
                    loop_time = (datetime.utcnow() - loop_start).total_seconds()
                    
                    # Wait before next update (target 1 minute per cycle)
                    wait_time = max(UPDATE_INTERVAL - loop_time, 1)
                    await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    self.logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(5)

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
        # Create bot instance
        bot = TradingBot()
        
        # Set event loop policy for Windows
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create and set event loop
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
            
            # Cancel pending tasks
            tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            if tasks:
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            
            # Clean shutdown
            loop.run_until_complete(loop.shutdown_asyncgens())
            
        finally:
            loop.close()
            
        # Wait for user input before exit on Windows
        if os.name == 'nt':
            input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()