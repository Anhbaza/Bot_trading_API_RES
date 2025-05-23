"""
Order data models
Author: Anhbaza01
Last Updated: 2025-05-23 10:57:53
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal

@dataclass
class OrderData:
    """Order data model"""
    symbol: str
    signal_type: str
    entry_price: Decimal
    current_price: Decimal
    take_profit: Decimal
    stop_loss: Decimal
    entry_time: datetime
    status: str
    pnl: Decimal = Decimal('0')
    pnl_percentage: Decimal = Decimal('0')
    close_time: Optional[datetime] = None
    close_reason: Optional[str] = None
    
    @property
    def duration(self) -> str:
        """Get order duration"""
        end_time = self.close_time or datetime.utcnow()
        duration = end_time - self.entry_time
        
        hours = duration.total_seconds() / 3600
        if hours < 1:
            minutes = duration.total_seconds() / 60
            return f"{minutes:.0f}m"
        return f"{hours:.1f}h"

    def update_price(self, new_price: Decimal, investment: Decimal = Decimal('100')) -> None:
        """Update current price and calculate P/L"""
        self.current_price = new_price
        
        # Calculate P/L
        if self.signal_type == "LONG":
            self.pnl_percentage = (self.current_price - self.entry_price) / self.entry_price * Decimal('100')
        else:  # SHORT
            self.pnl_percentage = (self.entry_price - self.current_price) / self.entry_price * Decimal('100')
            
        self.pnl = investment * self.pnl_percentage / Decimal('100')

    def check_close_conditions(self) -> Optional[str]:
        """Check if order should be closed"""
        if self.signal_type == "LONG":
            if self.current_price >= self.take_profit:
                return "Chạm Take Profit"
            elif self.current_price <= self.stop_loss:
                return "Chạm Stop Loss"
        else:  # SHORT
            if self.current_price <= self.take_profit:
                return "Chạm Take Profit"
            elif self.current_price >= self.stop_loss:
                return "Chạm Stop Loss"
        return None

    def close(self, reason: str) -> None:
        """Close the order"""
        self.status = "COMPLETED"
        self.close_time = datetime.utcnow()
        self.close_reason = reason

    @classmethod
    def from_signal(cls, signal_data: dict) -> 'OrderData':
        """Create order from signal data"""
        return cls(
            symbol=signal_data['symbol'],
            signal_type=signal_data['signal_type'],
            entry_price=Decimal(str(signal_data['entry'])),
            current_price=Decimal(str(signal_data['entry'])),
            take_profit=Decimal(str(signal_data['take_profit'])),
            stop_loss=Decimal(str(signal_data['stop_loss'])),
            entry_time=datetime.utcnow(),
            status="RUNNING"
        )
