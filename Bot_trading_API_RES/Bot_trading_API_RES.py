#!/usr/bin/env python3
"""
Trading Bot
Author: Anhbaza01
Version: 1.0.0
Last Updated: 2025-05-23 18:57:46 UTC
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
from binance.enums import *

# Import shared constants
from shared.constants import *
from shared.telegram_service import TelegramService

class TradingBot:
    def __init__(self):
        """Initialize trading bot"""
        self.logger = self._setup_logging()
        self.telegram = None
        self._is_running = True
        self.monitored_pairs = []
        self.active_signals = {}
        self.client = None
        self.last_update = datetime.utcnow()
        self.user = "Anhbaza01"  # Your login
        
        self.logger.info(f"Bot initialized at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        self.logger.info(f"User: {self.user}")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        try:
            # Create logs directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            logs_dir = os.path.join(current_dir, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            # Setup log file with date
            log_filename = os.path.join(
                logs_dir, 
                f'trading_bot_{datetime.utcnow().strftime("%Y%m%d")}.log'
            )
            
            # Configure logging
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

    async def setup_telegram(self, config: Dict[str, Any]) -> bool:
        """Setup Telegram notification service"""
        try:
            self.logger.info("Starting Telegram notification service...")
            
            if not config.get('telegram'):
                raise ValueError("Telegram configuration missing")
                
            self.telegram = TelegramService(
                token=config['telegram']['token'],
                chat_id=config['telegram']['chat_id']
            )
            
            if await self.telegram.test_connection():
                self.logger.info("Telegram service started successfully")
                return True
            else:
                raise ConnectionError("Failed to connect to Telegram")
            
        except Exception as e:
            self.logger.error(f"Telegram setup error: {str(e)}")
            return False

    def setup_binance(self, config: Dict[str, Any]) -> bool:
        """Setup Binance API client"""
        try:
            self.logger.info("Connecting to Binance...")
            
            # Initialize without API key for public endpoints only
            self.client = Client()
            
            # Test connection
            self.client.ping()
            self.logger.info("Connected to Binance API")
            
            return True
            
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Binance setup error: {str(e)}")
            return False

    async def get_trading_pairs(self) -> List[str]:
        """Get list of valid trading pairs"""
        try:
            valid_pairs = []
            
            # Get exchange info
            exchange_info = self.client.futures_exchange_info()
            
            # Get ticker information from futures API
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
            self.logger.info("Top 5 pairs by volume:")
            
            # Sort pairs by volume and show top 5
            top_pairs = sorted(
                [(p, volume_dict[p]) for p in valid_pairs],
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            for pair, volume in top_pairs:
                self.logger.info(f"  {pair}: ${volume:,.2f}")
            
            return valid_pairs
            
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Error getting trading pairs: {str(e)}")
            return []

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[Dict]:
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
            
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error getting klines for {symbol}: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Error getting klines for {symbol}: {str(e)}")
            return []

    def calculate_rsi(self, closes: List[float], period: int = RSI_PERIOD) -> Optional[float]:
        """Calculate RSI technical indicator"""
        try:
            if len(closes) < period + 1:
                return None
                
            # Calculate price changes
            deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            
            # Separate gains and losses
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            # Calculate average gains and losses
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            
            # Calculate smoothed RSI
            for i in range(period, len(deltas)):
                avg_gain = (avg_gain * 13 + gains[i]) / 14
                avg_loss = (avg_loss * 13 + losses[i]) / 14
            
            if avg_loss == 0:
                return 100
                
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return round(rsi, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {str(e)}")
            return None

    def check_volume_signal(self, klines: List[Dict]) -> Optional[str]:
        """Check for volume breakout signal"""
        try:
            if len(klines) < 20:
                return None
                
            # Get current candle data
            current = klines[-1]
            prev = klines[-2]
            
            # Calculate volume moving average
            volume_ma = sum(k['volume'] for k in klines[-20:-1]) / 19
            
            # Check volume increase
            volume_change = current['volume'] / volume_ma
            
            if volume_change >= VOLUME_RATIO_MIN:
                # Determine direction based on price action
                price_change = (current['close'] - current['open']) / current['open']
                prev_change = (prev['close'] - prev['open']) / prev['open']
                
                # Look for momentum
                if (price_change > 0 and prev_change > 0 and 
                    current['close'] > prev['close']):
                    return "LONG"
                elif (price_change < 0 and prev_change < 0 and 
                      current['close'] < prev['close']):
                    return "SHORT"
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking volume signal: {str(e)}")
            return None

    def calculate_targets(self, symbol: str, type: str, entry: float) -> Dict[str, float]:
        """Calculate take profit and stop loss levels"""
        try:
            # Get ATR for dynamic targets
            atr = self.calculate_atr(symbol)
            atr_multiplier = 2.0
            
            if type == "LONG":
                sl = entry - (atr * atr_multiplier)
                tp = entry + (atr * atr_multiplier * MIN_RR_RATIO)
            else:  # SHORT
                sl = entry + (atr * atr_multiplier)
                tp = entry - (atr * atr_multiplier * MIN_RR_RATIO)
            
            # Round to appropriate decimals
            symbol_info = next(
                (s for s in self.client.futures_exchange_info()['symbols'] 
                 if s['symbol'] == symbol),
                None
            )
            
            if symbol_info:
                price_filter = next(
                    (f for f in symbol_info['filters'] 
                     if f['filterType'] == 'PRICE_FILTER'),
                    None
                )
                
                if price_filter:
                    tick_size = float(price_filter['tickSize'])
                    decimals = len(str(tick_size).split('.')[-1].rstrip('0'))
                    
                    tp = round(tp, decimals)
                    sl = round(sl, decimals)
            
            return {
                'tp': tp,
                'sl': sl
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating targets: {str(e)}")
            return {
                'tp': 0,
                'sl': 0
            }

    def calculate_atr(self, symbol: str, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            klines = self.get_klines(symbol, '1h', period + 1)
            if not klines or len(klines) < period + 1:
                return 0
                
            true_ranges = []
            for i in range(1, len(klines)):
                high = klines[i]['high']
                low = klines[i]['low']
                prev_close = klines[i-1]['close']
                
                tr1 = high - low
                tr2 = abs(high - prev_close)
                tr3 = abs(low - prev_close)
                
                true_ranges.append(max(tr1, tr2, tr3))
                
            atr = sum(true_ranges) / len(true_ranges)
            return round(atr, 8)
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {str(e)}")
            return 0

    async def check_signals(self):
        """Check for trading signals"""
        try:
            signals_found = 0
            
            for symbol in self.monitored_pairs:
                # Skip if max trades reached for symbol
                if len([s for s in self.active_signals.values() 
                       if s['symbol'] == symbol]) >= MAX_TRADES_PER_SYMBOL:
                    continue
                    
                # Get klines data
                klines = self.get_klines(symbol, '1h')
                if not klines:
                    continue
                    
                # Calculate indicators
                closes = [k['close'] for k in klines]
                rsi = self.calculate_rsi(closes)
                
                if rsi is None:
                    continue
                    
                # Check conditions
                signal_type = None
                if rsi <= RSI_OVERSOLD:
                    vol_signal = self.check_volume_signal(klines)
                    if vol_signal == "LONG":
                        signal_type = "LONG"
                        
                elif rsi >= RSI_OVERBOUGHT:
                    vol_signal = self.check_volume_signal(klines)
                    if vol_signal == "SHORT":
                        signal_type = "SHORT"
                        
                # Generate signal
                if signal_type:
                    current_price = klines[-1]['close']
                    targets = self.calculate_targets(symbol, signal_type, current_price)
                    
                    if targets['tp'] and targets['sl']:
                        signal_id = f"{symbol}_{datetime.utcnow().timestamp()}"
                        
                        signal = {
                            'id': signal_id,
                            'symbol': symbol,
                            'type': signal_type,
                            'entry': current_price,
                            'tp': targets['tp'],
                            'sl': targets['sl'],
                            'time': datetime.utcnow(),
                            'rsi': rsi
                        }
                        
                        self.active_signals[signal_id] = signal
                        await self.send_signal(signal)
                        signals_found += 1
                        
            if signals_found > 0:
                self.logger.info(f"Found {signals_found} new signals")
                    
        except Exception as e:
            self.logger.error(f"Error checking signals: {str(e)}")

    async def send_signal(self, signal: Dict[str, Any]):
        """Send signal notification"""
        try:
            entry = signal['entry']
            tp = signal['tp']
            sl = signal['sl']
            
            if signal['type'] == "LONG":
                rr = abs((tp - entry) / (entry - sl))
            else:
                rr = abs((entry - tp) / (sl - entry))
                
            message = f"""
🔔 <b>Tín hiệu giao dịch mới</b>
📊 {signal['symbol']}
📈 {signal['type']}
📉 RSI: {signal['rsi']:.1f}
💰 Giá vào: ${signal['entry']:.2f}
✅ Take Profit: ${signal['tp']:.2f}
❌ Stop Loss: ${signal['sl']:.2f}
⚖️ R:R = {rr:.1f}
👤 {self.user}
⌚ {signal['time'].strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
            
            await self.telegram.send_message(message)
            self.logger.info(f"Sent signal for {signal['symbol']} {signal['type']}")
            
        except Exception as e:
            self.logger.error(f"Error sending signal: {str(e)}")

    async def update_signals(self):
        """Update and clean active signals"""
        try:
            if not self.active_signals:
                return
                
            signals_to_remove = []
            
            for signal_id, signal in self.active_signals.items():
                try:
                    # Get current price
                    ticker = self.client.futures_symbol_ticker(
                        symbol=signal['symbol']
                    )
                    current_price = float(ticker['price'])
                    
                    # Check if expired (24h)
                    if (datetime.utcnow() - signal['time']).total_seconds() > 86400:
                        await self.close_signal(signal_id, "EXPIRED", current_price)
                        signals_to_remove.append(signal_id)
                        continue
                        
                    # Check TP/SL
                    if signal['type'] == "LONG":
                        if current_price >= signal['tp']:
                            await self.close_signal(signal_id, "TP", current_price)
                            signals_to_remove.append(signal_id)
                        elif current_price <= signal['sl']:
                            await self.close_signal(signal_id, "SL", current_price)
                            signals_to_remove.append(signal_id)
                    else:  # SHORT
                        if current_price <= signal['tp']:
                            await self.close_signal(signal_id, "TP", current_price)
                            signals_to_remove.append(signal_id)
                        elif current_price >= signal['sl']:
                            await self.close_signal(signal_id, "SL", current_price)
                            signals_to_remove.append(signal_id)
                            
                except BinanceAPIException as e:
                    self.logger.error(f"Binance API error updating signal {signal_id}: {str(e)}")
                except Exception as e:
                    self.logger.error(f"Error updating signal {signal_id}: {str(e)}")
                    
            # Remove closed signals
            for signal_id in signals_to_remove:
                del self.active_signals[signal_id]
                
        except Exception as e:
            self.logger.error(f"Error updating signals: {str(e)}")

    async def close_signal(self, signal_id: str, reason: str, close_price: float):
        """Close a signal and send notification"""
        try:
            signal = self.active_signals[signal_id]
            
            entry = signal['entry']
            pnl = ((close_price - entry) / entry) * 100
            if signal['type'] == "SHORT":
                pnl *= -1
                
            time_in_trade = (datetime.utcnow() - signal['time']).total_seconds() / 3600
                
            message = f"""
🔒 <b>Tín hiệu đóng</b>
📊 {signal['symbol']}
📈 {signal['type']}
💰 Giá vào: ${entry:.2f}
💵 Giá đóng: ${close_price:.2f}
📊 P/L: {pnl:+.2f}%
⏱ Thời gian: {time_in_trade:.1f}h
📝 Lý do: {reason}
👤 {self.user}
⌚ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
            
            await self.telegram.send_message(message)
            self.logger.info(f"Closed signal {signal['symbol']} with {pnl:+.2f}% P/L")
            
        except Exception as e:
            self.logger.error(f"Error closing signal: {str(e)}")

    async def initialize(self) -> bool:
        """Initialize bot connections and settings"""
        try:
            # Load config
            config = self.load_config()
            if not config:
                return False
            
            # Setup connections
            if not self.setup_binance(config):
                return False
                
            if not await self.setup_telegram(config):
                return False
            
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

            # Main loop
            while self._is_running:
                try:
                    loop_start = datetime.utcnow()
                    
                    # Check signals
                    await self.check_signals()
                    
                    # Update active signals
                    await self.update_signals()
                    
                    # Calculate loop time
                    loop_time = (datetime.utcnow() - loop_start).total_seconds()
                    
                    # Wait before next update (target 1 minute per cycle)
                    wait_time = max(60 - loop_time, 1)
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