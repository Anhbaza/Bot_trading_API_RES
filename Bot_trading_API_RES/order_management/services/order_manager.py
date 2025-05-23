"""
Order management service
Author: Anhbaza01
Last Updated: 2025-05-23 11:06:41
"""

import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime

from shared.constants import (
    SIGNAL_TYPE_LONG, SIGNAL_TYPE_SHORT,
    ORDER_STATE_RUNNING, ORDER_STATE_COMPLETED,
    MAX_ACTIVE_ORDERS, INITIAL_INVESTMENT
)
from order_management.models.order_data import OrderData

class OrderManager:
    def __init__(self):
        """Initialize order manager"""
        self.logger = logging.getLogger("OrderManager")
        self.active_orders: Dict[str, OrderData] = {}
        self.completed_orders: List[OrderData] = []
        self.total_profit: Decimal = Decimal('0')
        self.win_count: int = 0
        self.loss_count: int = 0

    def can_add_order(self) -> bool:
        """Check if can add new order"""
        return len(self.active_orders) < MAX_ACTIVE_ORDERS

    def add_order(self, signal_data: dict) -> Optional[OrderData]:
        """Add new order from signal"""
        if not self.can_add_order():
            self.logger.warning("Cannot add order: Maximum active orders reached")
            return None

        try:
            symbol = signal_data['symbol']
            if symbol in self.active_orders:
                self.logger.warning(f"Symbol {symbol} already has active order")
                return None

            order = OrderData.from_signal(signal_data)
            self.active_orders[symbol] = order
            
            self.logger.info(
                f"Added new {order.signal_type} order for {symbol} at ${float(order.entry_price):.4f}"
            )
            return order

        except Exception as e:
            self.logger.error(f"Error adding order: {str(e)}")
            return None

    def update_order(
        self, 
        symbol: str, 
        current_price: Decimal,
        new_signal: Optional[dict] = None
    ) -> Tuple[Optional[OrderData], Optional[str]]:
        """
        Update order status and check for close conditions
        
        Args:
            symbol: Trading pair symbol
            current_price: Current price
            new_signal: New signal data if available
            
        Returns:
            Tuple of (updated order, close reason)
        """
        if symbol not in self.active_orders:
            return None, None

        order = self.active_orders[symbol]
        
        # Update price and P/L
        order.update_price(current_price, Decimal(str(INITIAL_INVESTMENT)))

        # Check signal reversal
        if new_signal and new_signal['signal_type'] != order.signal_type:
            return self.close_order(symbol, "Đảo chiều xu hướng"), "Đảo chiều xu hướng"

        # Check TP/SL
        close_reason = order.check_close_conditions()
        if close_reason:
            return self.close_order(symbol, close_reason), close_reason

        return order, None

    def close_order(self, symbol: str, reason: str) -> Optional[OrderData]:
        """Close order and update statistics"""
        if symbol not in self.active_orders:
            return None

        order = self.active_orders.pop(symbol)
        order.close(reason)

        # Update statistics
        self.total_profit += order.pnl
        if order.pnl > 0:
            self.win_count += 1
        else:
            self.loss_count += 1

        # Add to completed orders
        self.completed_orders.append(order)

        self.logger.info(
            f"Closed {order.signal_type} order for {symbol} - "
            f"Reason: {reason}, P/L: ${float(order.pnl):.2f}"
        )

        return order

    def get_active_symbols(self) -> List[str]:
        """Get list of active symbols"""
        return list(self.active_orders.keys())

    def get_statistics(self) -> Dict[str, float]:
        """Get trading statistics"""
        total_trades = self.win_count + self.loss_count
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0

        return {
            "total_profit": float(self.total_profit),
            "win_rate": win_rate,
            "total_trades": total_trades,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "active_orders": len(self.active_orders)
        }

    def get_order_summary(self, symbol: str) -> Optional[Dict[str, str]]:
        """Get summary of an order"""
        order = self.active_orders.get(symbol)
        if not order:
            return None

        return {
            "symbol": symbol,
            "type": order.signal_type,
            "entry": f"${float(order.entry_price):.4f}",
            "current": f"${float(order.current_price):.4f}",
            "pnl": f"${float(order.pnl):.2f}",
            "pnl_percent": f"{float(order.pnl_percentage):.2f}%",
            "duration": order.duration,
            "status": order.status
        }
