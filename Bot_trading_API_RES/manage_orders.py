#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
from datetime import datetime
import json
import yaml
from typing import Dict, Any, List, Optional
import tkinter as tk
from tkinter import ttk, messagebox
import threading

from shared.constants import *
from shared.telegram_service import TelegramService
from shared.database import Database

class Signal:
    def __init__(self, data: Dict[str, Any]):
        self.symbol = data['symbol']
        self.type = data['type']  # LONG or SHORT
        self.entry = float(data['entry'])
        self.tp = float(data['tp'])
        self.sl = float(data['sl'])
        self.timestamp = datetime.utcnow()

class Order:
    def __init__(self, signal: Signal):
        self.symbol = signal.symbol
        self.type = signal.type
        self.entry = signal.entry
        self.tp = signal.tp
        self.sl = signal.sl
        self.size = TRADE_SIZE_USDT
        self.current_price = signal.entry
        self.pnl = 0.0
        self.status = ORDER_STATE_OPEN
        self.entry_time = datetime.utcnow()
        self.close_time = None
        self.close_reason = None

    def update_price(self, price: float) -> Optional[str]:
        self.current_price = price
        price_change = (price - self.entry) / self.entry
        self.pnl = price_change * self.size * (1 if self.type == "LONG" else -1)
        
        if self.type == "LONG":
            if price >= self.tp:
                return CLOSE_REASON_TP
            elif price <= self.sl:
                return CLOSE_REASON_SL
        else:
            if price <= self.tp:
                return CLOSE_REASON_TP
            elif price >= self.sl:
                return CLOSE_REASON_SL
        return None

class OrderManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bot Quản Lý Lệnh")
        self.root.geometry("1200x800")
        
        # Data
        self.signals: List[Signal] = []
        self.active_orders: Dict[str, Order] = {}
        self.db = Database()
        
        # Setup UI
        self.setup_ui()
        self.update_ui()

    def setup_ui(self):
        """Setup UI components"""
        # Style
        style = ttk.Style()
        style.configure("Header.TLabel", font=("Arial", 12, "bold"))
        style.configure("Stats.TLabel", font=("Arial", 10))
        
        # Header Frame
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill=tk.X)
        
        ttk.Label(
            header_frame, 
            text="BOT QUẢN LÝ LỆNH GIAO DỊCH",
            style="Header.TLabel"
        ).pack(side=tk.LEFT)
        
        self.time_label = ttk.Label(
            header_frame,
            text="",
            style="Stats.TLabel"
        )
        self.time_label.pack(side=tk.RIGHT)
        
        # Stats Frame
        stats_frame = ttk.Frame(self.root, padding="10")
        stats_frame.pack(fill=tk.X)
        
        self.stats_label = ttk.Label(
            stats_frame,
            text="",
            style="Stats.TLabel"
        )
        self.stats_label.pack(side=tk.LEFT)
        
        # Signals Frame
        signals_frame = ttk.LabelFrame(
            self.root,
            text="Tín Hiệu Giao Dịch",
            padding="10"
        )
        signals_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Signals Table
        columns = ("ID", "Cặp", "Loại", "Giá vào", "TP", "SL", "R:R")
        self.signals_table = ttk.Treeview(
            signals_frame,
            columns=columns,
            show="headings",
            height=10
        )
        
        for col in columns:
            self.signals_table.heading(col, text=col)
            self.signals_table.column(col, width=100, anchor=tk.CENTER)
        
        self.signals_table.pack(fill=tk.BOTH, expand=True)
        
        # Buttons Frame
        buttons_frame = ttk.Frame(signals_frame, padding="10")
        buttons_frame.pack(fill=tk.X)
        
        ttk.Button(
            buttons_frame,
            text="Vào Lệnh",
            command=self.enter_selected_orders
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            buttons_frame,
            text="Làm Mới",
            command=self.refresh_signals
        ).pack(side=tk.LEFT, padx=5)
        
        # Orders Frame
        orders_frame = ttk.LabelFrame(
            self.root,
            text="Lệnh Đang Mở",
            padding="10"
        )
        orders_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Orders Table
        columns = ("Cặp", "Loại", "Giá vào", "Giá hiện tại", "P/L ($)", "P/L (%)", "Thời gian")
        self.orders_table = ttk.Treeview(
            orders_frame,
            columns=columns,
            show="headings",
            height=5
        )
        
        for col in columns:
            self.orders_table.heading(col, text=col)
            self.orders_table.column(col, width=100, anchor=tk.CENTER)
        
        self.orders_table.pack(fill=tk.BOTH, expand=True)
        
        # Close buttons
        close_frame = ttk.Frame(orders_frame, padding="10")
        close_frame.pack(fill=tk.X)
        
        ttk.Button(
            close_frame,
            text="Đóng Lệnh Đã Chọn",
            command=self.close_selected_orders
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            close_frame,
            text="Đóng Tất Cả",
            command=self.close_all_orders
        ).pack(side=tk.LEFT, padx=5)

    def update_ui(self):
        """Update UI elements"""
        # Update time
        self.time_label.config(
            text=f"⌚ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        
        # Update stats
        stats = self.db.get_stats()
        self.stats_label.config(
            text=(
                f"📊 Tổng lệnh: {stats['total_trades']} | "
                f"✅ Thắng: {stats['win_rate']:.1f}% | "
                f"💰 P/L: ${stats['total_pnl']:+,.2f} | "
                f"📈 Profit Factor: {stats['profit_factor']:.2f}"
            )
        )
        
        # Schedule next update
        self.root.after(1000, self.update_ui)

    def refresh_signals(self):
        """Refresh signals from trading bot"""
        # This would be replaced with real signal fetching
        self.signals = [
            Signal({
                'symbol': 'BTCUSDT',
                'type': 'LONG',
                'entry': 35000.0,
                'tp': 35700.0,
                'sl': 34650.0
            }),
            Signal({
                'symbol': 'ETHUSDT',
                'type': 'SHORT',
                'entry': 2000.0,
                'tp': 1950.0,
                'sl': 2025.0
            })
        ]
        
        # Update signals table
        self.signals_table.delete(*self.signals_table.get_children())
        
        for idx, signal in enumerate(self.signals, 1):
            rr = abs((signal.tp - signal.entry) / (signal.entry - signal.sl))
            
            self.signals_table.insert("", tk.END, values=(
                idx,
                signal.symbol,
                signal.type,
                f"${signal.entry:,.2f}",
                f"${signal.tp:,.2f}",
                f"${signal.sl:,.2f}",
                f"{rr:.1f}"
            ))

    def enter_selected_orders(self):
        """Enter selected orders"""
        selections = self.signals_table.selection()
        if not selections:
            messagebox.showwarning(
                "Chưa chọn lệnh",
                "Vui lòng chọn lệnh để vào"
            )
            return
            
        if len(self.active_orders) + len(selections) > MAX_TRADES:
            messagebox.showerror(
                "Quá số lệnh",
                f"Chỉ được phép mở tối đa {MAX_TRADES} lệnh"
            )
            return
            
        # Enter orders
        for item in selections:
            idx = int(self.signals_table.item(item)["values"][0]) - 1
            signal = self.signals[idx]
            
            if signal.symbol not in self.active_orders:
                order = Order(signal)
                self.active_orders[signal.symbol] = order
                self.db.add_order({
                    'symbol': order.symbol,
                    'type': order.type,
                    'entry_price': order.entry,
                    'take_profit': order.tp,
                    'stop_loss': order.sl,
                    'size': order.size
                })
        
        self.update_orders_table()
        messagebox.showinfo(
            "Thành công",
            f"Đã vào {len(selections)} lệnh"
        )

    def update_orders_table(self):
        """Update orders table"""
        self.orders_table.delete(*self.orders_table.get_children())
        
        for order in self.active_orders.values():
            pnl_pct = (order.pnl / order.size) * 100
            time_in_trade = (datetime.utcnow() - order.entry_time).total_seconds() / 60
            
            self.orders_table.insert("", tk.END, values=(
                order.symbol,
                order.type,
                f"${order.entry:,.2f}",
                f"${order.current_price:,.2f}",
                f"${order.pnl:+,.2f}",
                f"{pnl_pct:+.2f}%",
                f"{int(time_in_trade)}m"
            ))

    def close_selected_orders(self):
        """Close selected orders"""
        selections = self.orders_table.selection()
        if not selections:
            messagebox.showwarning(
                "Chưa chọn lệnh",
                "Vui lòng chọn lệnh để đóng"
            )
            return
            
        for item in selections:
            symbol = self.orders_table.item(item)["values"][0]
            if symbol in self.active_orders:
                order = self.active_orders[symbol]
                order.close_time = datetime.utcnow()
                order.close_reason = CLOSE_REASON_MANUAL
                order.status = ORDER_STATE_CLOSED
                
                self.db.update_order(order.symbol, {
                    'status': order.status,
                    'close_time': order.close_time,
                    'close_reason': order.close_reason,
                    'pnl': order.pnl
                })
                
                self.db.update_daily_stats(order.pnl)
                del self.active_orders[symbol]
        
        self.update_orders_table()
        messagebox.showinfo(
            "Thành công",
            f"Đã đóng {len(selections)} lệnh"
        )

    def close_all_orders(self):
        """Close all open orders"""
        if not self.active_orders:
            messagebox.showinfo(
                "Không có lệnh",
                "Không có lệnh nào đang mở"
            )
            return
            
        if messagebox.askyesno(
            "Xác nhận",
            "Bạn có chắc muốn đóng tất cả lệnh?"
        ):
            for order in self.active_orders.values():
                order.close_time = datetime.utcnow()
                order.close_reason = CLOSE_REASON_MANUAL
                order.status = ORDER_STATE_CLOSED
                
                self.db.update_order(order.symbol, {
                    'status': order.status,
                    'close_time': order.close_time,
                    'close_reason': order.close_reason,
                    'pnl': order.pnl
                })
                
                self.db.update_daily_stats(order.pnl)
            
            self.active_orders.clear()
            self.update_orders_table()
            messagebox.showinfo(
                "Thành công",
                "Đã đóng tất cả lệnh"
            )

def main():
    """Main entry point"""
    try:
        root = tk.Tk()
        app = OrderManagerGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror(
            "Lỗi",
            f"Lỗi không mong muốn: {str(e)}"
        )

if __name__ == "__main__":
    main()