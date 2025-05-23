"""
GUI window for order management
Author: Anhbaza01
Last Updated: 2025-05-23 10:57:53
"""

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
from typing import Dict, Any, Callable
from datetime import datetime
from decimal import Decimal

class OrderWindow:
    def __init__(
        self,
        on_signal_confirm: Callable[[list[str]], None],
        max_orders: int = 5,
        update_interval: float = 1.0
    ):
        """Initialize order management window"""
        self.window = tk.Tk()
        self.window.title("Quản lý Lệnh Giao dịch - Anhbaza01")
        self.window.geometry("1200x800")
        
        # Print debug message
        print("\n[DEBUG] GUI window initialized")
        
        self.max_orders = max_orders
        self.on_signal_confirm = on_signal_confirm
        self.update_interval = update_interval
        
        self._setup_gui()
        print("\n[DEBUG] GUI setup completed")


    def _setup_gui(self):
        """Setup GUI components"""
        # Statistics Frame
        stats_frame = ttk.LabelFrame(self.window, text="Thống kê", padding="5")
        stats_frame.pack(fill="x", padx=5, pady=5)

        self.profit_label = ttk.Label(stats_frame, text="Tổng lợi nhuận: $0.00")
        self.profit_label.pack(side="left", padx=5)

        self.win_rate_label = ttk.Label(stats_frame, text="Tỷ lệ thắng: 0%")
        self.win_rate_label.pack(side="left", padx=5)

        self.orders_count_label = ttk.Label(stats_frame, text=f"Lệnh đang mở: 0/{self.max_orders}")
        self.orders_count_label.pack(side="left", padx=5)

        # Signals Frame
        signals_frame = ttk.LabelFrame(self.window, text="Tín hiệu Mới", padding="5")
        signals_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Signals Treeview with Scrollbar
        signals_scroll = ttk.Scrollbar(signals_frame)
        signals_scroll.pack(side="right", fill="y")

        self.signals_tree = ttk.Treeview(
            signals_frame,
            columns=("Time", "Symbol", "Type", "Entry", "TP", "SL", "Confidence"),
            show="headings",
            yscrollcommand=signals_scroll.set
        )
        self.signals_tree.pack(fill="both", expand=True)
        signals_scroll.config(command=self.signals_tree.yview)

        # Setup signals columns
        self.signals_tree.heading("Time", text="Thời gian")
        self.signals_tree.heading("Symbol", text="Cặp tiền")
        self.signals_tree.heading("Type", text="Loại")
        self.signals_tree.heading("Entry", text="Giá vào")
        self.signals_tree.heading("TP", text="Take Profit")
        self.signals_tree.heading("SL", text="Stop Loss")
        self.signals_tree.heading("Confidence", text="Độ tin cậy")

        self.signals_tree.column("Time", width=120)
        self.signals_tree.column("Symbol", width=100)
        self.signals_tree.column("Type", width=80)
        self.signals_tree.column("Entry", width=100)
        self.signals_tree.column("TP", width=100)
        self.signals_tree.column("SL", width=100)
        self.signals_tree.column("Confidence", width=100)

        # Control buttons
        btn_frame = ttk.Frame(signals_frame)
        btn_frame.pack(fill="x", pady=5)

        confirm_btn = ttk.Button(
            btn_frame,
            text="✅ Xác nhận Vào Lệnh",
            command=self._handle_signal_confirm
        )
        confirm_btn.pack(side="left", padx=5)

        clear_btn = ttk.Button(
            btn_frame,
            text="🗑️ Xóa Tín hiệu",
            command=self._handle_clear_signals
        )
        clear_btn.pack(side="left", padx=5)

        # Active Orders Frame
        orders_frame = ttk.LabelFrame(self.window, text="Lệnh Đang Theo dõi", padding="5")
        orders_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Orders Treeview with Scrollbar
        orders_scroll = ttk.Scrollbar(orders_frame)
        orders_scroll.pack(side="right", fill="y")

        self.orders_tree = ttk.Treeview(
            orders_frame,
            columns=("Time", "Symbol", "Type", "Entry", "Current", "TP", "SL", "PnL", "PnL%", "Duration", "Status"),
            show="headings",
            yscrollcommand=orders_scroll.set
        )
        self.orders_tree.pack(fill="both", expand=True)
        orders_scroll.config(command=self.orders_tree.yview)

        # Setup orders columns
        columns = {
            "Time": ("Thời gian", 120),
            "Symbol": ("Cặp tiền", 100),
            "Type": ("Loại", 80),
            "Entry": ("Giá vào", 100),
            "Current": ("Giá hiện tại", 100),
            "TP": ("Take Profit", 100),
            "SL": ("Stop Loss", 100),
            "PnL": ("Lợi nhuận $", 100),
            "PnL%": ("Lợi nhuận %", 100),
            "Duration": ("Thời gian", 80),
            "Status": ("Trạng thái", 120)
        }

        for col, (text, width) in columns.items():
            self.orders_tree.heading(col, text=text)
            self.orders_tree.column(col, width=width)

        # Style configuration
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))

    def _setup_periodic_update(self):
        """Setup periodic GUI update"""
        def update():
            try:
                # Add your periodic update logic here
                pass
            finally:
                self.window.after(int(self.update_interval * 1000), update)
        update()

    def _handle_signal_confirm(self):
        """Handle signal confirmation button click"""
        selected = self.signals_tree.selection()
        if not selected:
            messagebox.showwarning(
                "Chưa chọn lệnh",
                "Vui lòng chọn lệnh muốn vào trước khi xác nhận!"
            )
            return

        if len(selected) > self.max_orders:
            messagebox.showerror(
                "Quá nhiều lệnh",
                f"Chỉ có thể vào tối đa {self.max_orders} lệnh cùng lúc!"
            )
            return

        symbols = []
        for item in selected:
            values = self.signals_tree.item(item)["values"]
            symbols.append(values[1])  # Symbol is at index 1
            self.signals_tree.delete(item)

        self.on_signal_confirm(symbols)

    def _handle_clear_signals(self):
        """Handle clear signals button click"""
        selected = self.signals_tree.selection()
        if not selected:
            return

        for item in selected:
            self.signals_tree.delete(item)

    def update_signals(self, signals: Dict[str, Dict[str, Any]]):
        """Update signals display"""
        try:
            print(f"\n[DEBUG] Updating signals in GUI: {signals}")
            
            # Add or update signals
            for symbol, data in signals.items():
                try:
                    values = (
                        datetime.now().strftime('%H:%M:%S'),
                        symbol,
                        data['signal_type'],
                        f"${float(data['entry']):.4f}",
                        f"${float(data['take_profit']):.4f}",
                        f"${float(data['stop_loss']):.4f}",
                        f"{float(data.get('confidence', 0.55)):.2%}"
                    )
                    
                    # Always insert as new
                    self.signals_tree.insert("", "end", values=values)
                    print(f"\n[DEBUG] Added signal for {symbol}")
                    
                except Exception as e:
                    print(f"\n[DEBUG] Error processing signal {symbol}: {str(e)}")
                    
        except Exception as e:
            print(f"\n[DEBUG] Error in update_signals: {str(e)}")

    def update_orders(self, orders: Dict[str, Any], stats: Dict[str, Any]):
        """Update orders display and statistics"""
        # Update statistics
        self.profit_label.config(text=f"Tổng lợi nhuận: ${stats['total_profit']:.2f}")
        self.win_rate_label.config(text=f"Tỷ lệ thắng: {stats['win_rate']:.1f}%")
        self.orders_count_label.config(text=f"Lệnh đang mở: {len(orders)}/{self.max_orders}")

        # Update orders
        for item in self.orders_tree.get_children():
            symbol = self.orders_tree.item(item)["values"][1]
            if symbol not in orders:
                self.orders_tree.delete(item)

        for symbol, order in orders.items():
            # Format values
            pnl = float(order.pnl)
            pnl_color = "gain" if pnl >= 0 else "loss"
            
            values = (
                order.entry_time.strftime('%H:%M:%S'),
                symbol,
                order.signal_type,
                f"${float(order.entry_price):.4f}",
                f"${float(order.current_price):.4f}",
                f"${float(order.take_profit):.4f}",
                f"${float(order.stop_loss):.4f}",
                f"${pnl:.2f}",
                f"{float(order.pnl_percentage):.2f}%",
                order.duration,
                order.status
            )
            
            # Find existing item
            found = False
            for item in self.orders_tree.get_children():
                if self.orders_tree.item(item)["values"][1] == symbol:
                    self.orders_tree.item(item, values=values, tags=(pnl_color,))
                    found = True
                    break
            
            # Add new item
            if not found:
                self.orders_tree.insert("", "end", values=values, tags=(pnl_color,))

        # Configure colors
        self.orders_tree.tag_configure("gain", foreground="green")
        self.orders_tree.tag_configure("loss", foreground="red")

    def run(self):
        """Start the GUI main loop"""
        try:
            self.window.mainloop()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi không mong muốn: {str(e)}")
            raise
