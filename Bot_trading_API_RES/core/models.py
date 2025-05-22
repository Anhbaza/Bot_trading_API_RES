"""
Core data models for Bot Trading API REST
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

@dataclass
class OrderBookLevel:
    """Order book price level"""
    price: float
    quantity: float
    orders: int = 1
    is_bid: bool = True

@dataclass
class MarketState:
    """Market state at a given timestamp"""
    timestamp: datetime
    current_price: float
    vol_ratio: float  # Bid/ask volume ratio
    cnt_ratio: float  # Bid/ask count ratio
    spread: float
    bid_vol: float
    ask_vol: float
    bid_cnt: int
    ask_cnt: int
    rsi_5m: float = 50.0
    ma20_5m: float = 0.0
    ma50_15m: float = 0.0

@dataclass
class MarketTrend:
    """Market trend analysis"""
    type: str  # 'ACCUMULATION', 'DISTRIBUTION', 'NEUTRAL'
    strength: float  # 0.0 - 5.0
    signal: Optional[str]  # 'LONG', 'SHORT', None
    timestamp: datetime
    price: float
    metrics: Dict[str, float]
    confidence: float  # 0.0 - 1.0

@dataclass
class VolumeZone:
    """Volume zone data"""
    price_level: float
    long_volume: float
    short_volume: float
    order_count: int

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

@dataclass
class TradingPosition:
    """Active trading position data"""
    symbol: str
    position_type: str
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    pnl: float
    status: str