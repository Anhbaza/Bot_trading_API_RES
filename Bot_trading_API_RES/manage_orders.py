#!/usr/bin/env python3
"""
Order Manager Bot
Author: Anhbaza01
Version: 1.0.0
Last Updated: 2025-05-23 19:54:17 UTC

This bot manages trading signals and order execution
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import yaml

from shared.constants import *
from shared.telegram_service import TelegramService
from shared.websocket_manager import WebSocketManager, MessageType

class OrderManager:
    def __init__(self):
        """Initialize Order Manager"""
        self.logger = self._setup_logging()
        self.telegram = None
        self.ws_manager = None
        self._is_running = True
        self.active_signals: Dict[str, Dict] = {}
        self.watched_pairs: List[str] = []
        self.user = "Anhbaza01"

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            logs_dir = os.path.join(current_dir, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            log_filename = os.path.join(
                logs_dir, 
                f'order_manager_{datetime.utcnow().strftime("%Y%m%d")}.log'
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
            
            logger = logging.getLogger("OrderManager")
            
            logger.info("="*50)
            logger.info("Order Manager - Logging Initialized")
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
            return logging.getLogger("OrderManager")

    async def handle_new_signal(self, data: Dict[str, Any]):
        """Handle new trading signal"""
        try:
            signal_id = data.get('id')
            if not signal_id:
                self.logger.error("[-] Received signal without ID")
                return

            self.logger.info(
                f"[+] New signal received:\n"
                f"    Symbol: {data.get('symbol')}\n"
                f"    Type: {data.get('type')}\n"
                f"    Entry: {data.get('entry')}\n"
                f"    TP: {data.get('tp')}\n"
                f"    SL: {data.get('sl')}\n"
                f"    Confidence: {data.get('confidence')}%"
            )
            
            # Store signal
            self.active_signals[signal_id] = data
            
            # Update UI or notify user
            await self.update_signal_display()
            
        except Exception as e:
            self.logger.error(f"[-] Error handling new signal: {str(e)}")

    async def handle_signal_update(self, data: Dict[str, Any]):
        """Handle signal update"""
        try:
            signal_id = data.get('id')
            if signal_id not in self.active_signals:
                self.logger.warning(f"[!] Update for unknown signal: {signal_id}")
                return
                
            self.logger.info(
                f"[*] Signal updated:\n"
                f"    Symbol: {data.get('symbol')}\n"
                f"    New TP: {data.get('tp')}\n"
                f"    New SL: {data.get('sl')}"
            )
            
            # Update stored signal
            self.active_signals[signal_id].update(data)
            
            # Update UI
            await self.update_signal_display()
            
        except Exception as e:
            self.logger.error(f"[-] Error handling signal update: {str(e)}")

    async def handle_signal_close(self, data: Dict[str, Any]):
        """Handle signal close"""
        try:
            signal_id = data.get('id')
            if signal_id not in self.active_signals:
                self.logger.warning(f"[!] Close for unknown signal: {signal_id}")
                return
                
            signal = self.active_signals[signal_id]
            self.logger.info(
                f"[*] Signal closed:\n"
                f"    Symbol: {signal.get('symbol')}\n"
                f"    Type: {signal.get('type')}\n"
                f"    Reason: {data.get('close_reason')}"
            )
            
            # Remove from active signals
            del self.active_signals[signal_id]
            
            # Update UI
            await self.update_signal_display()
            
        except Exception as e:
            self.logger.error(f"[-] Error handling signal close: {str(e)}")

    async def update_watched_pairs(self, pairs: List[str]):
        """Update watched pairs list"""
        try:
            self.watched_pairs = pairs
            self.logger.info(f"[+] Updated watched pairs: {', '.join(pairs)}")
            
            # Notify trading bot
            if self.ws_manager:
                await self.ws_manager.update_watched_pairs(pairs)
                
        except Exception as e:
            self.logger.error(f"[-] Error updating watched pairs: {str(e)}")

    async def reset_to_scan_all(self):
        """Reset to scanning all pairs"""
        try:
            self.watched_pairs = []
            self.logger.info("[*] Reset to scanning all pairs")
            
            # Notify trading bot
            if self.ws_manager:
                await self.ws_manager.reset_to_scan_all()
                
        except Exception as e:
            self.logger.error(f"[-] Error resetting scan mode: {str(e)}")

    async def update_signal_display(self):
        """Update signal display in console"""
        try:
            # Clear console
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Print header
            print("\n=== Order Manager ===")
            print(f"Time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Active Signals: {len(self.active_signals)}")
            print(f"Watched Pairs: {len(self.watched_pairs)}")
            print("="*20)
            
            # Print active signals
            if self.active_signals:
                print("\nActive Signals:")
                for signal in self.active_signals.values():
                    print(
                        f"\n{signal['symbol']} - {signal['type']}\n"
                        f"Entry: {signal['entry']:.2f}\n"
                        f"TP: {signal['tp']:.2f}\n"
                        f"SL: {signal['sl']:.2f}\n"
                        f"Confidence: {signal.get('confidence', 0)}%"
                    )
            else:
                print("\nNo active signals")
                
            # Print watched pairs
            if self.watched_pairs:
                print("\nWatched Pairs:")
                print(", ".join(self.watched_pairs))
            else:
                print("\nScanning all pairs")
                
        except Exception as e:
            self.logger.error(f"[-] Error updating display: {str(e)}")

    async def setup_websocket(self) -> bool:
        """Setup WebSocket connection"""
        try:
            self.ws_manager = WebSocketManager(
                name="OrderManager",
                logger=self.logger
            )
            
            # Register message handlers
            self.ws_manager.register_handler(
                MessageType.NEW_SIGNAL.value,
                self.handle_new_signal
            )
            self.ws_manager.register_handler(
                MessageType.UPDATE_SIGNAL.value,
                self.handle_signal_update
            )
            self.ws_manager.register_handler(
                MessageType.CLOSE_SIGNAL.value,
                self.handle_signal_close
            )
            
            if await self.ws_manager.connect():
                # Start listening in background
                asyncio.create_task(self.ws_manager.listen())
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"[-] WebSocket setup error: {str(e)}")
            return False

    async def initialize(self) -> bool:
        """Initialize manager connections and settings"""
        try:
            # Setup WebSocket
            if not await self.setup_websocket():
                self.logger.error("[-] Failed to setup WebSocket")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"[-] Initialization error: {str(e)}")
            return False

    async def run(self):
        """Main manager loop"""
        try:
            # Initialize
            if not await self.initialize():
                self.logger.error("[-] Failed to initialize. Check logs.")
                return

            self.logger.info("[+] Order Manager started successfully")
            self.logger.info(f"[*] Current time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")

            while self._is_running:
                try:
                    # Update display
                    await self.update_signal_display()
                    
                    # Wait before next update
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"[-] Error in main loop: {str(e)}")
                    await asyncio.sleep(5)

        except KeyboardInterrupt:
            self.logger.info("[*] Manager stopped by user")
        except Exception as e:
            self.logger.error(f"[-] Fatal error: {str(e)}")
        finally:
            self._is_running = False
            if self.ws_manager:
                await self.ws_manager.stop()
            self.logger.info("[*] Manager stopped")

def main():
    """Main entry point"""
    try:
        # Create manager instance
        manager = OrderManager()
        
        # Set event loop policy for Windows
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create and set event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run manager
        loop.run_until_complete(manager.run())
        
    except KeyboardInterrupt:
        print("\n[!] Manager stopped by user")
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
            
        finally:
            loop.close()
            
        # Wait for user input before exit on Windows
        if os.name == 'nt':
            input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()