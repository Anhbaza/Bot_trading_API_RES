#!/usr/bin/env python3
"""
Trading Bot with WebSocket Communication
Author: Anhbaza01
Version: 1.0.0
Last Updated: 2025-05-23 20:08:23 UTC

This bot monitors crypto pairs and generates trading signals
"""

import os
import sys
import asyncio
import logging
import json
import yaml
from datetime import datetime
from datetime import  timedelta  # Thêm import timedelta
from typing import Dict, Any, List, Optional, Tuple
from binance.client import Client
from binance.exceptions import BinanceAPIException
from shared.console_manager import ConsoleManager

from shared.constants import (
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    CONFIDENCE_THRESHOLD,
    VOLUME_RATIO_MIN,
    SCAN_MODE_ALL,
    SCAN_MODE_WATCHED
)
from shared.telegram_service import TelegramService
from shared.signal_processor import SignalProcessor
from shared.websocket_manager import WebSocketManager, MessageType

class TradingBot:
    def __init__(self):
        self.user = "Anhbaza01"
        self.logger = self._setup_logging()
        self.telegram = None
        self.ws_manager = None
        self._is_running = True
        self.monitored_pairs = []
        self.watched_pairs = []
        self.active_signals = {}
        self.client = None
        self.signal_processor = None
        self.scanning_mode = SCAN_MODE_ALL
        self.update_interval = 300  # 5 minutes
        self.min_volume_usdt = 1000000  # $1M volume minimum
        
        # Khởi tạo console ở cuối để đảm bảo các biến khác đã được khởi tạo
        self.console = None
        
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
            
            logger = logging.getLogger("TradingBot")
            
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
            return logging.getLogger("TradingBot")

    async def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'config.yaml'
            )
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Load Telegram config
            telegram_config = config.get('telegram', {})
            self.telegram = TelegramService(
                token=telegram_config.get('token'),
                chat_id=telegram_config.get('chat_id'),
                logger=self.logger
            )
            
            # Load trading config
            trading_config = config.get('trading', {})
            self.update_interval = trading_config.get('update_interval', 300)
            self.min_volume_usdt = trading_config.get('min_volume_usdt', 1000000)
            
            self.logger.info("[+] Configuration loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"[-] Error loading config: {str(e)}")
            return False

    async def setup_binance(self) -> bool:
        """Setup Binance API connection"""
        try:
            self.logger.info("[*] Connecting to Binance...")
            
            # Initialize without API keys for public data only
            self.client = Client()
            
            # Test connection
            server_time = self.client.get_server_time()
            if not server_time:
                raise ConnectionError("Could not get server time")
                
            self.logger.info("[+] Connected to Binance API")
            return True
            
        except Exception as e:
            self.logger.error(f"[-] Binance setup error: {str(e)}")
            return False

    async def setup_websocket(self) -> bool:
        """Setup WebSocket connection"""
        try:
            self.logger.info("[*] Setting up WebSocket connection...")
            
            self.ws_manager = WebSocketManager(
                name="TradingBot",
                logger=self.logger,
                reconnect_interval=5,
                heartbeat_interval=30
            )
            
            # Try to connect multiple times at startup
            max_attempts = 3
            for attempt in range(max_attempts):
                self.logger.info(f"[*] Connection attempt {attempt + 1}/{max_attempts}")
                
                if await self.ws_manager.connect():
                    # Register message handlers
                    self.ws_manager.register_handler(
                        MessageType.WATCH_PAIRS.value,
                        self.handle_watch_pairs
                    )
                    self.ws_manager.register_handler(
                        MessageType.SCAN_ALL.value,
                        self.handle_scan_all
                    )
                    
                    # Start listening in background
                    asyncio.create_task(self.ws_manager.listen())
                    return True
                    
                if attempt < max_attempts - 1:  # Don't wait after last attempt
                    await asyncio.sleep(5)
            
            self.logger.error(
                f"[-] Failed to connect after {max_attempts} attempts. "
                "Check if WebSocket server is running."
            )
            return False
            
        except Exception as e:
            self.logger.error(f"[-] WebSocket setup error: {str(e)}")
            return False

    async def get_valid_pairs(self) -> List[str]:
        """Get list of valid trading pairs"""
        try:
            # Get exchange info
            info = self.client.get_exchange_info()
            
            # Get 24hr stats for volume filtering
            tickers = self.client.get_ticker()
            volume_dict = {
                t['symbol']: float(t['quoteVolume']) 
                for t in tickers
            }
            
            # Filter valid pairs
            valid_pairs = []
            for symbol in info['symbols']:
                # Check if pair is valid for trading
                if (symbol['status'] == 'TRADING' and
                    symbol['quoteAsset'] == 'USDT' and
                    symbol['symbol'] in volume_dict and
                    volume_dict[symbol['symbol']] >= self.min_volume_usdt):
                    valid_pairs.append(symbol['symbol'])
            
            # Sort by volume
            valid_pairs.sort(
                key=lambda x: volume_dict[x],
                reverse=True
            )
            
            self.logger.info(f"[+] Found {len(valid_pairs)} valid pairs")
            
            # Log top 5 pairs by volume
            self.logger.info("Top 5 pairs by volume:")
            for pair in valid_pairs[:5]:
                volume = volume_dict[pair]
                self.logger.info(
                    f"  {pair}: ${volume:,.2f}"
                )
            
            return valid_pairs
            
        except Exception as e:
            self.logger.error(f"[-] Error getting valid pairs: {str(e)}")
            return []

    async def get_klines(self, symbol: str) -> Optional[List[Dict]]:
        """Get kline data for a symbol"""
        try:
            # Get 100 15-minute candles
            klines = self.client.get_klines(
                symbol=symbol,
                interval=Client.KLINE_INTERVAL_15MINUTE,
                limit=100
            )
            
            # Convert to dict format
            formatted_klines = []
            for k in klines:
                formatted_klines.append({
                    'time': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'close_time': k[6],
                    'quote_volume': float(k[7])
                })
                
            return formatted_klines
            
        except BinanceAPIException as e:
            self.logger.error(f"[-] Binance API error getting klines for {symbol}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"[-] Error getting klines for {symbol}: {str(e)}")
            return None

    async def process_signal(self, symbol: str, klines: List[Dict]) -> Optional[Dict]:
        """Process and generate trading signal"""
        try:
            # Log start of processing
            self.logger.info(f"[SCAN] Analyzing {symbol}...")

            # Check data validity
            if not klines:
                self.logger.info(f"[-] {symbol}: No kline data available")
                return None
                
            if len(klines) < 50:
                self.logger.info(f"[-] {symbol}: Insufficient kline data (need 50, got {len(klines)})")
                return None
                
            # Calculate RSI
            closes = [k['close'] for k in klines]
            rsi = self.signal_processor._calculate_rsi(closes)
            
            if rsi is None:
                self.logger.info(f"[-] {symbol}: Failed to calculate RSI")
                return None
                
            # Log RSI value
            if rsi <= RSI_OVERSOLD:
                self.logger.info(f"[+] {symbol}: RSI = {rsi:.2f} (Oversold)")
            elif rsi >= RSI_OVERBOUGHT:
                self.logger.info(f"[+] {symbol}: RSI = {rsi:.2f} (Overbought)")
            else:
                self.logger.info(f"[-] {symbol}: RSI = {rsi:.2f} (Neutral)")
            
            # Check conditions for signal
            signal_type = None
            if rsi <= RSI_OVERSOLD:
                volume_signal = self.signal_processor.check_volume_signal(klines)
                if volume_signal == "LONG":
                    self.logger.info(f"[+] {symbol}: Volume breakout confirmed for LONG")
                    signal_type = "LONG"
                else:
                    self.logger.info(f"[-] {symbol}: No volume confirmation for LONG")
                    
            elif rsi >= RSI_OVERBOUGHT:
                volume_signal = self.signal_processor.check_volume_signal(klines)
                if volume_signal == "SHORT":
                    self.logger.info(f"[+] {symbol}: Volume breakout confirmed for SHORT")
                    signal_type = "SHORT"
                else:
                    self.logger.info(f"[-] {symbol}: No volume confirmation for SHORT")
                    
            if signal_type:
                current_price = klines[-1]['close']
                self.logger.info(f"[*] {symbol}: Calculating targets for {signal_type} @ {current_price}")
                
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
                    
                    # Calculate confidence
                    signal['confidence'] = self.signal_processor.calculate_confidence(signal, klines)
                    
                    if signal['confidence'] >= CONFIDENCE_THRESHOLD:
                        self.logger.info(
                            f"[!] {symbol}: SIGNAL FOUND!\n"
                            f"    Type: {signal_type}\n"
                            f"    Entry: {current_price:.2f}\n"
                            f"    TP: {targets['tp']:.2f}\n"
                            f"    SL: {targets['sl']:.2f}\n"
                            f"    Confidence: {signal['confidence']}%"
                        )
                        return signal
                    else:
                        self.logger.info(
                            f"[-] {symbol}: Low confidence ({signal['confidence']}% < {CONFIDENCE_THRESHOLD}%)"
                        )
                else:
                    self.logger.info(f"[-] {symbol}: Invalid TP/SL levels")
            
            return None
            
        except Exception as e:
            self.logger.error(f"[ERROR] Processing {symbol}: {str(e)}")
            return None

    def calculate_targets(
        self, 
        symbol: str, 
        signal_type: str, 
        entry_price: float
    ) -> Dict[str, Optional[float]]:
        """Calculate take profit and stop loss levels"""
        try:
            # Get symbol info for price precision
            info = self.client.get_symbol_info(symbol)
            precision = len(info['filters'][0]['tickSize'].rstrip('0').split('.')[1])
            
            if signal_type == "LONG":
                tp = round(entry_price * 1.02, precision)  # 2% profit
                sl = round(entry_price * 0.99, precision)  # 1% loss
            else:  # SHORT
                tp = round(entry_price * 0.98, precision)  # 2% profit
                sl = round(entry_price * 1.01, precision)  # 1% loss
                
            return {'tp': tp, 'sl': sl}
            
        except Exception as e:
            self.logger.error(f"[-] Error calculating targets for {symbol}: {str(e)}")
            return {'tp': None, 'sl': None}

    async def handle_watch_pairs(self, data: Dict[str, Any]):
        """Handle watched pairs update"""
        try:
            pairs = data.get('pairs', [])
            self.watched_pairs = pairs
            self.scanning_mode = SCAN_MODE_WATCHED
            
            self.logger.info(
                f"[+] Updated watched pairs: "
                f"Monitoring {len(pairs)} pairs"
            )
            
            if pairs:
                self.logger.info(f"[*] Pairs: {', '.join(pairs)}")
            
        except Exception as e:
            self.logger.error(f"[-] Error handling watch pairs: {str(e)}")

    async def handle_scan_all(self, data: Dict[str, Any]):
        """Handle reset to scan all pairs"""
        try:
            self.watched_pairs = []
            self.scanning_mode = SCAN_MODE_ALL
            
            self.logger.info(
                f"[+] Reset to scanning all pairs "
                f"(Total: {len(self.monitored_pairs)})"
            )
            
        except Exception as e:
            self.logger.error(f"[-] Error handling scan all: {str(e)}")

    async def initialize(self) -> bool:
        """Initialize bot connections and settings"""
        try:
            # Khởi tạo console trước khi load config
            self.console = ConsoleManager("Trading Bot")
            self.console.start()
            
            # Load config
            if not await self.load_config():
                self.logger.error("[-] Failed to load config")
                return False
                
            # Setup Binance connection
            if not await self.setup_binance():
                self.logger.error("[-] Failed to setup Binance")
                return False
                
            # Setup WebSocket
            if not await self.setup_websocket():
                self.logger.error("[-] Failed to setup WebSocket")
                return False
                
            # Initialize signal processor
            self.signal_processor = SignalProcessor(logger=self.logger)
            
            # Get valid trading pairs
            self.monitored_pairs = await self.get_valid_pairs()
            if not self.monitored_pairs:
                self.logger.error("[-] No valid pairs found")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"[-] Initialization error: {str(e)}")
            return False
    async def scan_pairs(self):
        """Scan trading pairs for signals"""
        try:
            pairs_to_scan = (
                self.watched_pairs if self.scanning_mode == SCAN_MODE_WATCHED
                else self.monitored_pairs
            )
            
            self.logger.info(
                f"[*] Scanning {len(pairs_to_scan)} pairs "
                f"({'watched' if self.scanning_mode == SCAN_MODE_WATCHED else 'all'})"
            )
            
            for symbol in pairs_to_scan:
                try:
                    # Get klines
                    klines = await self.get_klines(symbol)
                    if not klines:
                        continue
                        
                    # Process for signals
                    new_signal = await self.process_signal(symbol, klines)
                    
                    if new_signal:
                        # Store signal
                        self.active_signals[new_signal['id']] = new_signal
                        
                        # Send to order manager
                        if self.ws_manager:
                            await self.ws_manager.send_signal(new_signal)
                            
                        # Notify on Telegram
                        if self.telegram:
                            await self.telegram.send_signal(new_signal)
                    
                except Exception as e:
                    self.logger.error(f"[-] Error scanning {symbol}: {str(e)}")
                    continue
                    
                # Small delay between pairs
                await asyncio.sleep(0.5)
                
        except Exception as e:
            self.logger.error(f"[-] Error in scan_pairs: {str(e)}")
    async def update_display(self):
        """Update console display"""
        try:
            # Clear console
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Print header
            print("\n=== Trading Bot Status ===")
            print(f"Time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"User: {self.user}")
            print("="*25)
            
            # Print scanning mode
            mode = "WATCHED PAIRS" if self.scanning_mode == SCAN_MODE_WATCHED else "ALL PAIRS"
            print(f"\nScanning Mode: {mode}")
            
            # Print pairs being monitored
            pairs_to_scan = self.watched_pairs if self.scanning_mode == SCAN_MODE_WATCHED else self.monitored_pairs
            print(f"Monitoring: {len(pairs_to_scan)} pairs")
            
            if self.scanning_mode == SCAN_MODE_WATCHED and self.watched_pairs:
                print("\nWatched Pairs:")
                print(", ".join(self.watched_pairs))
            
            # Print active signals
            if self.active_signals:
                print("\nActive Signals:")
                for signal_id, signal in self.active_signals.items():
                    print(
                        f"\n{signal['symbol']} - {signal['type']}\n"
                        f"Entry: {signal['entry']:.8f}\n"
                        f"TP: {signal['tp']:.8f}\n"
                        f"SL: {signal['sl']:.8f}\n"
                        f"RSI: {signal['rsi']:.2f}\n"
                        f"Confidence: {signal.get('confidence', 0)}%"
                    )
            else:
                print("\nNo active signals")
            
            # Print next scan time
            next_scan = datetime.utcnow().timestamp() + self.update_interval
            next_scan_time = datetime.fromtimestamp(next_scan).strftime('%H:%M:%S')
            print(f"\nNext scan at: {next_scan_time} UTC")
            
            # Print connection status
            ws_status = "[CONNECTED]" if self.ws_manager and self.ws_manager.is_connected() else "[DISCONNECTED]"
            print(f"\nWebSocket: {ws_status}")
            
            # Print last few log messages
            print("\nRecent Logs:")
            print("-" * 50)
            
        except Exception as e:
            self.logger.error(f"[-] Error updating display: {str(e)}")
    async def run(self):
        """Main bot loop"""
        try:
            # Initialize
            if not await self.initialize():
                self.logger.error("[-] Failed to initialize. Check logs.")
                return

            self.logger.info("[+] Bot started successfully")
            self.logger.info(f"[*] Monitoring {len(self.monitored_pairs)} pairs")
            self.logger.info(f"[*] Current time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"[*] User: {self.user}")

            # Send startup notification
            if self.telegram:
                await self.telegram.send_message(
                    f"🤖 Bot started\n"
                    f"Monitoring {len(self.monitored_pairs)} pairs\n"
                    f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                )

            while self._is_running:
                try:
                    # Calculate next scan time
                    next_scan = datetime.utcnow()
                    next_scan = next_scan.replace(
                        second=0, 
                        microsecond=0
                    ) + timedelta(minutes=5)

                    # Update console
                    if self.console:
                        self.console.update(
                            scanning_mode="WATCHED PAIRS" if self.scanning_mode == SCAN_MODE_WATCHED else "ALL PAIRS",
                            total_pairs=len(self.watched_pairs if self.scanning_mode == SCAN_MODE_WATCHED else self.monitored_pairs),
                            watched_pairs=self.watched_pairs,
                            active_signals=self.active_signals,
                            next_scan=next_scan,
                            ws_connected=self.ws_manager.is_connected() if self.ws_manager else False,
                            user=self.user
                        )
                    
                    # Scan pairs
                    await self.scan_pairs()
                    
                    # Wait for next update with console updates
                    for _ in range(self.update_interval):
                        if not self._is_running:
                            break
                        await asyncio.sleep(1)
                        if self.console:
                            self.console.update(
                                scanning_mode="WATCHED PAIRS" if self.scanning_mode == SCAN_MODE_WATCHED else "ALL PAIRS",
                                total_pairs=len(self.watched_pairs if self.scanning_mode == SCAN_MODE_WATCHED else self.monitored_pairs),
                                watched_pairs=self.watched_pairs,
                                active_signals=self.active_signals,
                                next_scan=next_scan,
                                ws_connected=self.ws_manager.is_connected() if self.ws_manager else False,
                                user=self.user
                            )
                    
                except Exception as e:
                    self.logger.error(f"[-] Error in main loop: {str(e)}")
                    await asyncio.sleep(5)

        except KeyboardInterrupt:
            self.logger.info("[*] Bot stopped by user")
        except Exception as e:
            self.logger.error(f"[-] Fatal error: {str(e)}")
        finally:
            self._is_running = False
            if self.ws_manager:
                await self.ws_manager.stop()
            if self.console:
                self.console.stop()
            self.logger.info("[*] Bot stopped")
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
        print("\n[!] Bot stopped by user")
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {str(e)}")
    finally:
        try:
            loop = asyncio.get_event_loop()
            
            # Cancel pending tasks
            tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            if tasks:
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            
            # Clean shutdown
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            
        except Exception as e:
            print(f"\n[ERROR] Error during shutdown: {str(e)}")
        
        # Restore terminal
        if 'bot' in locals() and bot.console:
            bot.console.stop()
        
        # Wait for user input before exit on Windows
        if os.name == 'nt':
            input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()