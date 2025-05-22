"""
Data model entities for Bot Trading API REST
Defines the core data structures used throughout the system
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
from enum import Enum

@dataclass
class OrderBookLevel:
    """A price level in the order book"""
    price: float
    quantity: float
    orders: int = 1
    is_bid: bool = True

    def __post_init__(self):
        """Validate after initialization"""
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.orders < 1:
            raise ValueError("Orders must be at least 1")

@dataclass
class MarketState:
    """Market state at a specific point in time"""
    timestamp: datetime
    current_price: float
    vol_ratio: float  # Bid/Ask volume ratio
    cnt_ratio: float  # Bid/Ask count ratio
    spread: float
    bid_vol: float
    ask_vol: float
    bid_cnt: int
    ask_cnt: int
    rsi_5m: float = 50.0
    ma20_5m: float = 0.0
    ma50_15m: float = 0.0

    def __post_init__(self):
        """Validate after initialization"""
        if self.current_price <= 0:
            raise ValueError("Current price must be positive")
        if self.spread < 0:
            raise ValueError("Spread cannot be negative")

@dataclass
class MarketTrend:
    """Market trend analysis result"""
    type: str  # 'ACCUMULATION', 'DISTRIBUTION', 'NEUTRAL'
    strength: float  # 0.0 - 5.0
    signal: Optional[str]  # 'LONG', 'SHORT', None
    timestamp: datetime
    price: float
    metrics: Dict[str, float]
    confidence: float  # 0.0 - 1.0

    def __post_init__(self):
        """Validate after initialization"""
        valid_types = {'ACCUMULATION', 'DISTRIBUTION', 'NEUTRAL'}
        if self.type not in valid_types:
            raise ValueError(f"Invalid trend type. Must be one of {valid_types}")
        if not 0 <= self.strength <= 5:
            raise ValueError("Strength must be between 0 and 5")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")

@dataclass
class VolumeZone:
    """Volume zone in the order book"""
    price_level: float
    long_volume: float
    short_volume: float
    order_count: int

    def __post_init__(self):
        """Validate after initialization"""
        if self.price_level <= 0:
            raise ValueError("Price level must be positive")
        if self.long_volume < 0:
            raise ValueError("Long volume cannot be negative")
        if self.short_volume < 0:
            raise ValueError("Short volume cannot be negative")
        if self.order_count < 0:
            raise ValueError("Order count cannot be negative")

@dataclass
class SignalData:
    """Trading signal data"""
    symbol: str
    signal_type: str  # 'LONG' or 'SHORT'
    entry: float
    stop_loss: float
    take_profit: float
    reason: str
    timestamp: str
    confidence: float = 0.0
    volume: float = 0.0
    leverage: int = 1
    
    def __post_init__(self):
        """Validate after initialization"""
        if self.signal_type not in {'LONG', 'SHORT'}:
            raise ValueError("Signal type must be 'LONG' or 'SHORT'")
        if self.entry <= 0:
            raise ValueError("Entry price must be positive")
        if self.stop_loss <= 0:
            raise ValueError("Stop loss must be positive")
        if self.take_profit <= 0:
            raise ValueError("Take profit must be positive")

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"

@dataclass
class TradingPosition:
    """Active trading position"""
    symbol: str
    position_type: str  # 'LONG' or 'SHORT'
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    volume: float
    leverage: int
    entry_time: datetime
    last_update: datetime
    pnl: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    
    def update_pnl(self, current_price: float):
        """Update position PNL"""
        self.current_price = current_price
        multiplier = 1 if self.position_type == 'LONG' else -1
        self.pnl = multiplier * (current_price - self.entry_price) / self.entry_price * 100 * self.leverage
        self.last_update = datetime.utcnow()

@dataclass
class TradingStats:
    """Trading statistics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_update: datetime = field(default_factory=datetime.utcnow)
    trade_history: List[Dict] = field(default_factory=list)
    
    def update_stats(self, trade_result: Dict):
        """Update trading statistics with new trade result"""
        self.total_trades += 1
        self.total_pnl += trade_result['pnl']
        
        if trade_result['pnl'] > 0:
            self.winning_trades += 1
            self.average_win = (self.average_win * (self.winning_trades - 1) + trade_result['pnl']) / self.winning_trades
        else:
            self.losing_trades += 1
            self.average_loss = (self.average_loss * (self.losing_trades - 1) + trade_result['pnl']) / self.losing_trades
        
        self.win_rate = self.winning_trades / self.total_trades * 100
        self.last_update = datetime.utcnow()
        self.trade_history.append(trade_result)
        
        # Update max drawdown
        cumulative_pnl = 0
        peak = 0
        for trade in self.trade_history:
            cumulative_pnl += trade['pnl']
            peak = max(peak, cumulative_pnl)
            drawdown = peak - cumulative_pnl
            self.max_drawdown = max(self.max_drawdown, drawdown)
