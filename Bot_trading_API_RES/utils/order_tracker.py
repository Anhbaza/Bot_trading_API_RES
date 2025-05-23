from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
from typing import Dict, List
import telegram
from prometheus_client import Counter, Gauge
import tkinter as tk
from tkinter import ttk

class OrderStatus(Enum):
    RUNNING = "ĐANG CHẠY"
    SUCCESS = "THÀNH CÔNG"
    FAILED = "THẤT BẠI"

@dataclass
class Order:
    symbol: str
    entry_price: float
    direction: str  # "LONG" hoặc "SHORT"
    take_profit: float
    stop_loss: float
    entry_time: datetime
    status: OrderStatus = OrderStatus.RUNNING
    profit_loss: float = 0.0
    initial_investment: float = 100.0  # Mặc định đầu tư $100

class OrderTracker:
    def __init__(self, telegram_token: str, chat_id: str):
        self.orders: Dict[str, Order] = {}
        self.bot = telegram.Bot(token=telegram_token)
        self.chat_id = chat_id
        
        # Metrics
        self.total_orders = Counter('trading_bot_total_orders', 'Tổng số lệnh đã tạo')
        self.successful_orders = Counter('trading_bot_successful_orders', 'Số lệnh thành công')
        self.failed_orders = Counter('trading_bot_failed_orders', 'Số lệnh thất bại')
        self.current_profit = Gauge('trading_bot_current_profit', 'Tổng lợi nhuận/lỗ hiện tại')
        
        # Khởi tạo cửa sổ theo dõi
        self.init_monitoring_window()

    def init_monitoring_window(self):
        self.window = tk.Tk()
        self.window.title("Theo Dõi Bot Giao Dịch")
        self.window.geometry("400x300")
        
        # Tạo nhãn
        self.total_orders_label = tk.Label(self.window, text="Tổng số lệnh: 0")
        self.total_orders_label.pack()
        
        self.success_rate_label = tk.Label(self.window, text="Tỷ lệ thành công: 0%")
        self.success_rate_label.pack()
        
        self.profit_label = tk.Label(self.window, text="Tổng lợi nhuận: $0")
        self.profit_label.pack()
        
        # Tạo danh sách lệnh
        self.order_tree = ttk.Treeview(self.window, columns=("Symbol", "Trạng thái", "Lợi nhuận"), show="headings")
        self.order_tree.heading("Symbol", text="Cặp tiền")
        self.order_tree.heading("Trạng thái", text="Trạng thái")
        self.order_tree.heading("Lợi nhuận", text="Lợi nhuận ($)")
        self.order_tree.pack(fill=tk.BOTH, expand=1)
        
        # Bắt đầu vòng lặp cập nhật
        self.window.after(1000, self.update_monitor)

    async def add_order(self, symbol: str, entry_price: float, direction: str, 
                       take_profit: float, stop_loss: float):
        order = Order(
            symbol=symbol,
            entry_price=entry_price,
            direction=direction,
            take_profit=take_profit,
            stop_loss=stop_loss,
            entry_time=datetime.now()
        )
        self.orders[symbol] = order
        self.total_orders.inc()
        
        await self.send_telegram_message(
            f"🔔 Lệnh Mới Được Tạo:\n"
            f"Cặp tiền: {symbol}\n"
            f"Hướng: {direction}\n"
            f"Giá vào: ${entry_price:.2f}\n"
            f"Take Profit: ${take_profit:.2f}\n"
            f"Stop Loss: ${stop_loss:.2f}\n"
            f"Trạng thái: {order.status.value}"
        )

    async def update_order(self, symbol: str, current_price: float, new_direction: str = None):
        if symbol not in self.orders:
            return
        
        order = self.orders[symbol]
        
        # Kiểm tra đảo chiều xu hướng
        if new_direction and new_direction != order.direction:
            await self.close_order(symbol, current_price, "Đảo chiều xu hướng")
            return
        
        # Cập nhật TP và SL nếu cùng hướng
        if new_direction and new_direction == order.direction:
            await self.send_telegram_message(
                f"📊 Cập nhật lệnh - {symbol}:\n"
                f"TP trước đó: ${order.take_profit:.2f}\n"
                f"SL trước đó: ${order.stop_loss:.2f}\n"
            )
            return

        # Kiểm tra chạm TP hoặc SL
        pl = self.calculate_profit_loss(order, current_price)
        if order.direction == "LONG":
            if current_price >= order.take_profit:
                await self.close_order(symbol, current_price, "Chạm Take Profit")
            elif current_price <= order.stop_loss:
                await self.close_order(symbol, current_price, "Chạm Stop Loss")
        else:  # SHORT
            if current_price <= order.take_profit:
                await self.close_order(symbol, current_price, "Chạm Take Profit")
            elif current_price >= order.stop_loss:
                await self.close_order(symbol, current_price, "Chạm Stop Loss")

    async def close_order(self, symbol: str, current_price: float, reason: str):
        order = self.orders[symbol]
        pl = self.calculate_profit_loss(order, current_price)
        
        order.profit_loss = pl
        order.status = OrderStatus.SUCCESS if pl > 0 else OrderStatus.FAILED
        
        if order.status == OrderStatus.SUCCESS:
            self.successful_orders.inc()
        else:
            self.failed_orders.inc()
        
        self.current_profit.inc(pl)
        
        await self.send_telegram_message(
            f"🔚 Đóng Lệnh - {symbol}:\n"
            f"Lý do: {reason}\n"
            f"Lợi nhuận/Lỗ: ${pl:.2f}\n"
            f"Trạng thái: {order.status.value}"
        )

    def calculate_profit_loss(self, order: Order, current_price: float) -> float:
        if order.direction == "LONG":
            return order.initial_investment * ((current_price - order.entry_price) / order.entry_price)
        else:  # SHORT
            return order.initial_investment * ((order.entry_price - current_price) / order.entry_price)

    async def send_telegram_message(self, message: str):
        await self.bot.send_message(chat_id=self.chat_id, text=message)

    def update_monitor(self):
        # Cập nhật thống kê
        total = self.total_orders._value.get()
        successful = self.successful_orders._value.get()
        success_rate = (successful / total * 100) if total > 0 else 0
        total_profit = self.current_profit._value.get()
        
        # Cập nhật nhãn
        self.total_orders_label.config(text=f"Tổng số lệnh: {total}")
        self.success_rate_label.config(text=f"Tỷ lệ thành công: {success_rate:.1f}%")
        self.profit_label.config(text=f"Tổng lợi nhuận: ${total_profit:.2f}")
        
        # Cập nhật danh sách lệnh
        self.order_tree.delete(*self.order_tree.get_children())
        for symbol, order in self.orders.items():
            self.order_tree.insert("", "end", values=(
                symbol,
                order.status.value,
                f"${order.profit_loss:.2f}"
            ))
        
        # Lên lịch cập nhật tiếp theo
        self.window.after(1000, self.update_monitor)
