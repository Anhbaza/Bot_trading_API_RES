#!/usr/bin/env python3
"""
Order Manager Bot
Author: Anhbaza01
Last Updated: 2025-05-23 17:14:10 UTC
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
import json
import yaml
from typing import Dict, Any, List, Optional
import curses
from curses import wrapper
import aiohttp
from telegram import Bot
from telegram.error import TelegramError

class Order:
    def __init__(self, symbol: str, type: str, entry: float, tp: float, sl: float):
        self.symbol = symbol
        self.type = type  # LONG or SHORT
        self.entry = entry
        self.take_profit = tp
        self.stop_loss = sl
        self.current_price = entry
        self.pnl = 0.0
        self.size = 100  # Fixed size $100 per trade
        self.status = "PENDING"
        self.entry_time = datetime.utcnow()
        self.close_time = None
        self.close_reason = None
        
    def update_price(self, price: float):
        """Update current price and calculate PnL"""
        self.current_price = price
        price_change = (price - self.entry) / self.entry
        self.pnl = price_change * self.size * (1 if self.type == "LONG" else -1)
        
        # Check TP/SL
        if self.type == "LONG":
            if price >= self.take_profit:
                return "TP"
            elif price <= self.stop_loss:
                return "SL"
        else:  # SHORT
            if price <= self.take_profit:
                return "TP"
            elif price >= self.stop_loss:
                return "SL"
                
        return None
        
    def close(self, reason: str):
        """Close the order"""
        self.status = "CLOSED"
        self.close_time = datetime.utcnow()
        self.close_reason = reason

class ConsoleUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.selected_index = 0
        self.signals = []  # List of available signals
        self.selected_pairs = []  # Selected pairs for trading
        self.active_orders: Dict[str, Order] = {}  # Active orders being monitored
        self.closed_orders: List[Order] = []  # History of closed orders
        self.total_pnl = 0.0  # Total profit/loss
        self.view_mode = "SIGNALS"  # SIGNALS or ORDERS view
        
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)
        
        self.GREEN = curses.color_pair(1)
        self.CYAN = curses.color_pair(2)
        self.YELLOW = curses.color_pair(3)
        self.RED = curses.color_pair(4)
        self.HIGHLIGHT = curses.color_pair(5)

    def draw_header(self):
        """Draw header with stats"""
        # Title
        title = " BOT QUẢN LÝ LỆNH GIAO DỊCH "
        self.stdscr.addstr(0, (self.width - len(title)) // 2, title, self.YELLOW | curses.A_BOLD)
        
        # Info line
        time_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        info = f" ⌚ {time_str} UTC | 👤 Anhbaza01 | 💰 P/L: ${self.total_pnl:+,.2f} "
        self.stdscr.addstr(1, 2, info, self.GREEN)
        
        # Stats
        stats = f" 📊 Lệnh đang mở: {len(self.active_orders)}/5 | ✅ Lệnh đã đóng: {len(self.closed_orders)} "
        self.stdscr.addstr(1, self.width - len(stats) - 2, stats, self.CYAN)
        
        # Mode
        mode = " SIGNALS " if self.view_mode == "SIGNALS" else " ORDERS "
        self.stdscr.addstr(2, 2, mode, self.HIGHLIGHT)
        
        # Separator
        self.stdscr.addstr(3, 1, "─" * (self.width-2), self.CYAN)

    def draw_signals_view(self):
        """Draw signals selection view"""
        # Headers
        header_y = 5
        self.stdscr.addstr(header_y, 2, "ID  │ Cặp      │ Loại │ Giá vào     │ TP          │ SL          │ Status", self.CYAN)
        self.stdscr.addstr(header_y + 1, 2, "───┼──────────┼──────┼────────────┼────────────┼────────────┼────────", self.CYAN)
        
        # List signals
        for idx, signal in enumerate(self.signals):
            y = header_y + 2 + idx
            if y < self.height - 4:
                # Highlight selected row
                attr = self.HIGHLIGHT if idx == self.selected_index else curses.A_NORMAL
                
                # ID and symbol
                self.stdscr.addstr(y, 2, f"{idx+1:2d}", attr)
                self.stdscr.addstr(y, 4, " │ ")
                symbol_attr = self.YELLOW if signal['symbol'] in self.selected_pairs else attr
                self.stdscr.addstr(y, 7, f"{signal['symbol']:<8}", symbol_attr)
                
                # Type
                self.stdscr.addstr(y, 15, " │ ")
                type_attr = self.GREEN if signal['type'] == "LONG" else self.RED
                self.stdscr.addstr(y, 17, f"{signal['type']:<4}", type_attr)
                
                # Entry
                self.stdscr.addstr(y, 21, " │ ")
                self.stdscr.addstr(y, 23, f"${signal['entry']:>9,.2f}", attr)
                
                # TP
                self.stdscr.addstr(y, 32, " │ ")
                self.stdscr.addstr(y, 34, f"${signal['tp']:>9,.2f}", self.GREEN)
                
                # SL
                self.stdscr.addstr(y, 43, " │ ")
                self.stdscr.addstr(y, 45, f"${signal['sl']:>9,.2f}", self.RED)
                
                # Status
                self.stdscr.addstr(y, 54, " │ ")
                status = "SELECTED" if signal['symbol'] in self.selected_pairs else "AVAILABLE"
                status_attr = self.YELLOW if status == "SELECTED" else attr
                self.stdscr.addstr(y, 56, f"{status:<8}", status_attr)

    def draw_orders_view(self):
        """Draw active orders view"""
        # Headers
        header_y = 5
        self.stdscr.addstr(header_y, 2, "Cặp      │ Loại │ Giá vào     │ Giá hiện tại │ P/L ($)  │ P/L (%) │ Thời gian", self.CYAN)
        self.stdscr.addstr(header_y + 1, 2, "─────────┼──────┼────────────┼──────────────┼──────────┼─────────┼──────────", self.CYAN)
        
        # List active orders
        for idx, (symbol, order) in enumerate(self.active_orders.items()):
            y = header_y + 2 + idx
            if y < self.height - 4:
                # Symbol
                self.stdscr.addstr(y, 2, f"{order.symbol:<8}", self.YELLOW)
                
                # Type
                self.stdscr.addstr(y, 10, " │ ")
                type_attr = self.GREEN if order.type == "LONG" else self.RED
                self.stdscr.addstr(y, 12, f"{order.type:<4}", type_attr)
                
                # Entry price
                self.stdscr.addstr(y, 16, " │ ")
                self.stdscr.addstr(y, 18, f"${order.entry:>9,.2f}")
                
                # Current price
                self.stdscr.addstr(y, 27, " │ ")
                self.stdscr.addstr(y, 29, f"${order.current_price:>11,.2f}")
                
                # P/L amount
                self.stdscr.addstr(y, 40, " │ ")
                pnl_attr = self.GREEN if order.pnl >= 0 else self.RED
                self.stdscr.addstr(y, 42, f"${order.pnl:>+7,.2f}", pnl_attr)
                
                # P/L percent
                self.stdscr.addstr(y, 49, " │ ")
                pnl_pct = (order.pnl / order.size) * 100
                self.stdscr.addstr(y, 51, f"{pnl_pct:>+6.2f}%", pnl_attr)
                
                # Time
                self.stdscr.addstr(y, 57, " │ ")
                time_str = (datetime.utcnow() - order.entry_time).total_seconds() // 60
                self.stdscr.addstr(y, 59, f"{int(time_str):>3}m")

    def draw_status(self):
        """Draw status bar"""
        y = self.height - 2
        if self.view_mode == "SIGNALS":
            # Show selected pairs
            selected = ", ".join(self.selected_pairs) if self.selected_pairs else "Chưa chọn cặp nào"
            status = f" Đã chọn: {selected}"
            self.stdscr.addstr(y - 1, 2, status, self.GREEN)
            
            # Show controls
            controls = " ↑/↓: Di chuyển | SPACE: Chọn/Bỏ | ENTER: Vào lệnh | TAB: Xem lệnh | ESC: Thoát "
            self.stdscr.addstr(y, (self.width - len(controls)) // 2, controls, self.CYAN)
        else:
            # Show orders summary
            if self.active_orders:
                total_pnl = sum(order.pnl for order in self.active_orders.values())
                summary = f" Tổng P/L hiện tại: ${total_pnl:+,.2f}"
                self.stdscr.addstr(y - 1, 2, summary, self.GREEN if total_pnl >= 0 else self.RED)
            
            # Show controls
            controls = " TAB: Xem tín hiệu | ESC: Thoát "
            self.stdscr.addstr(y, (self.width - len(controls)) // 2, controls, self.CYAN)

    def update(self):
        """Update screen"""
        self.stdscr.clear()
        self.draw_header()
        
        if self.view_mode == "SIGNALS":
            self.draw_signals_view()
        else:
            self.draw_orders_view()
            
        self.draw_status()
        self.stdscr.refresh()

    def handle_input(self) -> Optional[Dict[str, Any]]:
        """Handle keyboard input"""
        key = self.stdscr.getch()
        
        if key == 9:  # TAB
            self.view_mode = "ORDERS" if self.view_mode == "SIGNALS" else "SIGNALS"
            
        elif self.view_mode == "SIGNALS":
            if key == curses.KEY_UP and self.selected_index > 0:
                self.selected_index -= 1
            elif key == curses.KEY_DOWN and self.selected_index < len(self.signals) - 1:
                self.selected_index += 1
            elif key == ord(' '):  # Spacebar
                signal = self.signals[self.selected_index]
                symbol = signal['symbol']
                
                if symbol in self.selected_pairs:
                    self.selected_pairs.remove(symbol)
                elif len(self.selected_pairs) < 5:
                    self.selected_pairs.append(symbol)
                    
            elif key == 10:  # Enter
                if self.selected_pairs:
                    return {
                        "action": "ENTER_ORDERS",
                        "pairs": self.selected_pairs
                    }
                    
        if key == 27:  # ESC
            return {"action": "EXIT"}
            
        return None

class OrderManager:
    def __init__(self):
        self.logger = self._setup_logging()
        self.telegram = None
        self._is_running = True
        self.signals = []
        self.ui = None
        
        print("\n[DEBUG] OrderManager initialized")

    async def setup_telegram(self):
        """Setup Telegram bot"""
        try:
            # Load config
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'config.yaml')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Initialize bot
            self.telegram = Bot(token=config['telegram']['token'])
            self.chat_id = config['telegram']['chat_id']
            
            # Test connection
            await self.telegram.get_me()
            return True
            
        except Exception as e:
            self.logger.error(f"Telegram setup error: {str(e)}")
            return False

    def run_ui(self, stdscr) -> Optional[List[str]]:
        """Run the console UI"""
        try:
            # Setup curses
            curses.use_default_colors()
            curses.curs_set(0)
            stdscr.nodelay(0)
            stdscr.timeout(100)

            # Initialize UI
            self.ui = ConsoleUI(stdscr)
            
            # Main UI loop
            while True:
                self.ui.update()
                result = self.ui.handle_input()
                
                if result:
                    if result["action"] == "EXIT":
                        return None
                    elif result["action"] == "ENTER_ORDERS":
                        return result["pairs"]
                        
                # Update prices every second
                if self.ui.active_orders:
                    # This would be replaced with real price updates
                    for order in self.ui.active_orders.values():
                        # Simulate price movement for demo
                        price_change = float(datetime.utcnow().second) / 100
                        new_price = order.entry * (1 + price_change)
                        
                        # Update order
                        result = order.update_price(new_price)
                        if result:  # TP or SL hit
                            order.close(result)
                            self.ui.total_pnl += order.pnl
                            self.ui.closed_orders.append(order)
                            del self.ui.active_orders[order.symbol]

        except Exception as e:
            self.logger.error(f"UI error: {str(e)}")
            return None

    async def run(self):
        """Main bot loop"""
        try:
            print("\n=== BOT QUẢN LÝ LỆNH GIAO DỊCH ===")
            print(f"⌚ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"👤 User: Anhbaza01")
            print("="*40)

            # Setup Telegram
            if not await self.setup_telegram():
                print("\n❌ Lỗi kết nối Telegram")
                return

            # Run UI
            selected_pairs = wrapper(self.run_ui)
            if not selected_pairs:
                print("\n👋 Tạm biệt!")
                return

            print("\n✅ Đã vào lệnh:")
            for pair in selected_pairs:
                print(f"  └─ {pair}")
                
            # Notify trading bot
            await self.telegram.send_message(
                chat_id=self.chat_id,
                text=f"🎯 BOT QUẢN LÝ LỆNH\n"
                     f"📊 Đã vào lệnh: {', '.join(selected_pairs)}\n"
                     f"⌚ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

        except Exception as e:
            self.logger.error(f"Fatal error: {str(e)}")
        finally:
            self._is_running = False

def main():
    """Main entry point"""
    try:
        # Create and start bot
        manager = OrderManager()
        
        # Set event loop policy for Windows
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run bot
        loop.run_until_complete(manager.run())
        
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