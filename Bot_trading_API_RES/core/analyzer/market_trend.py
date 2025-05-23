"""
Market trend analyzer component
Analyzes market trends and calculates trend confidence
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from binance import Client

from ..models import MarketState, MarketTrend, VolumeZone
from ..utils.calculations import calculate_delta, calculate_ma, calculate_rsi

class MarketTrendAnalyzer:
    def __init__(self, 
                 api_key: str, 
                 api_secret: str, 
                 symbol: str = "",
                 depth_limit: int = 100,
                 price_range_percent: float = 1.0,
                 vol_threshold: float = 1.5,
                 cnt_threshold: float = 1.5,
                 history_size: int = 100):
        """Initialize Market Trend Analyzer"""
        self.client = Client(api_key, api_secret)
        self.symbol = symbol
        self.depth_limit = depth_limit
        self.price_range_percent = price_range_percent
        self.vol_threshold = vol_threshold
        self.cnt_threshold = cnt_threshold
        self.history_size = history_size
        
        # State storage
        self.history: List[MarketState] = []
        self.last_trend: Optional[MarketTrend] = None
        
        # Analysis parameters
        self.STRONG_TREND_THRESHOLD = 1.5
        self.VERY_STRONG_TREND_THRESHOLD = 2.0
        self.MIN_CONFIDENCE_THRESHOLD = 0.7
        
        # Setup logging
        self.logger = logging.getLogger(__name__)

    def get_order_book_state(self) -> Optional[MarketState]:
        """Get and analyze current orderbook state"""
        try:
            # Get current price
            ticker = self.client.get_symbol_ticker(symbol=self.symbol)
            current_price = float(ticker['price'])
            
            # Calculate price range
            price_range = current_price * (self.price_range_percent / 100)
            price_min = current_price - price_range
            price_max = current_price + price_range
            
            # Get orderbook
            depth = self.client.get_order_book(symbol=self.symbol, limit=self.depth_limit)
            
            # Analyze bids and asks
            bids = [(float(p), float(q)) for p, q in depth['bids'] 
                    if price_min <= float(p) <= price_max]
            asks = [(float(p), float(q)) for p, q in depth['asks'] 
                    if price_min <= float(p) <= price_max]
            
            # Calculate ratios
            bid_vol = sum(q for _, q in bids)
            ask_vol = sum(q for _, q in asks)
            bid_cnt = len(bids)
            ask_cnt = len(asks)
            
            vol_ratio = bid_vol / ask_vol if ask_vol else float('inf')
            cnt_ratio = bid_cnt / ask_cnt if ask_cnt else float('inf')
            spread = asks[0][0] - bids[0][0] if asks and bids else 0
            
            # Get technical indicators
            klines_5m = self.client.get_klines(symbol=self.symbol, interval='5m', limit=200)
            klines_15m = self.client.get_klines(symbol=self.symbol, interval='15m', limit=200)
            
            rsi_5m = calculate_rsi(klines_5m)
            ma20_5m = calculate_ma(klines_5m, 20)
            ma50_15m = calculate_ma(klines_15m, 50)
            
            # Create market state
            state = MarketState(
                timestamp=datetime.utcnow(),
                current_price=current_price,
                vol_ratio=vol_ratio,
                cnt_ratio=cnt_ratio,
                spread=spread,
                bid_vol=bid_vol,
                ask_vol=ask_vol,
                bid_cnt=bid_cnt,
                ask_cnt=ask_cnt,
                rsi_5m=rsi_5m,
                ma20_5m=ma20_5m,
                ma50_15m=ma50_15m
            )
            
            # Update history
            self.history.append(state)
            if len(self.history) > self.history_size:
                self.history.pop(0)
                
            return state
            
        except Exception as e:
            self.logger.error(f"Error getting orderbook for {self.symbol}: {str(e)}")
            return None

    def analyze_trend(self) -> Optional[MarketTrend]:
        """Analyze current market trend"""
        try:
            # Get market state
            state = self.get_order_book_state()
            if not state:
                return None
                
            vr, cr = state.vol_ratio, state.cnt_ratio
            
            # Get additional klines data
            klines_5m = self.client.get_klines(symbol=self.symbol, interval='5m', limit=100)
            klines_15m = self.client.get_klines(symbol=self.symbol, interval='15m', limit=100)
            
            # Calculate indicators
            delta_5m = calculate_delta(klines_5m)
            delta_15m = calculate_delta(klines_15m)
            ma20 = calculate_ma(klines_5m, 20)
            ma50 = calculate_ma(klines_15m, 50)
            
            # Determine trend
            if (vr > self.vol_threshold and cr > self.cnt_threshold and
                delta_5m > 0 and delta_15m > 0 and
                state.current_price > ma20 > ma50):
                trend_type = 'ACCUMULATION'
                strength = min(vr / self.vol_threshold, cr / self.cnt_threshold)
                signal = 'LONG'
                
            elif (vr < 1/self.vol_threshold and cr < 1/self.cnt_threshold and
                  delta_5m < 0 and delta_15m < 0 and
                  state.current_price < ma20 < ma50):
                trend_type = 'DISTRIBUTION'
                strength = min(1/(vr * self.vol_threshold), 1/(cr * self.cnt_threshold))
                signal = 'SHORT'
                
            else:
                trend_type = 'NEUTRAL'
                strength = 0.0
                signal = None

            # Calculate confidence and create trend object
            if trend_type != 'NEUTRAL':
                confidence = self._calculate_trend_confidence(state, trend_type)
                if confidence < self.MIN_CONFIDENCE_THRESHOLD:
                    trend_type = 'NEUTRAL'
                    strength = 0.0
                    signal = None
                    confidence = 0.0
            else:
                confidence = 0.0
                
            trend = MarketTrend(
                type=trend_type,
                strength=strength,
                signal=signal,
                timestamp=datetime.utcnow(),
                price=state.current_price,
                metrics={
                    'volume_ratio': vr,
                    'count_ratio': cr,
                    'spread': state.spread,
                    'rsi_5m': state.rsi_5m,
                    'ma20_5m': ma20,
                    'ma50_15m': ma50,
                    'delta_5m': delta_5m,
                    'delta_15m': delta_15m
                },
                confidence=confidence
            )
            
            self.last_trend = trend
            return trend
            
        except Exception as e:
            self.logger.error(f"Error analyzing trend for {self.symbol}: {str(e)}")
            return None

    def _calculate_trend_confidence(self, state: MarketState, trend_type: str) -> float:
        """Calculate trend confidence score"""
        confidence = 0.0
        weights = {
            'vol_ratio': 0.3,
            'cnt_ratio': 0.2,
            'rsi': 0.2,
            'ma': 0.2,
            'spread': 0.1
        }
        
        if trend_type == 'ACCUMULATION':
            if state.vol_ratio > self.vol_threshold:
                confidence += weights['vol_ratio']
            if state.cnt_ratio > self.cnt_threshold:
                confidence += weights['cnt_ratio']
            if state.rsi_5m < 65:
                confidence += weights['rsi']
            if state.current_price > state.ma20_5m > state.ma50_15m:
                confidence += weights['ma']
            if state.spread < 0.001:
                confidence += weights['spread']
                
        elif trend_type == 'DISTRIBUTION':
            if state.vol_ratio < 1/self.vol_threshold:
                confidence += weights['vol_ratio']
            if state.cnt_ratio < 1/self.cnt_threshold:
                confidence += weights['cnt_ratio']
            if state.rsi_5m > 35:
                confidence += weights['rsi']
            if state.current_price < state.ma20_5m < state.ma50_15m:
                confidence += weights['ma']
            if state.spread < 0.001:
                confidence += weights['spread']
                
        return confidence
    def get_market_state(self) -> MarketState:
        """Get current market state with enhanced metrics"""
        try:
            # Get current price
            ticker = self.client.get_symbol_ticker(symbol=self.symbol)
            current_price = float(ticker['price'])
            
            # Get orderbook
            depth = self.client.get_order_book(symbol=self.symbol, limit=self.depth_limit)
            
            # Get klines for technical indicators
            klines_5m = self.client.get_klines(symbol=self.symbol, interval='5m', limit=200)
            klines_15m = self.client.get_klines(symbol=self.symbol, interval='15m', limit=200)
            
            # Calculate basic metrics
            price_range = current_price * (self.price_range_percent / 100)
            price_min = current_price - price_range
            price_max = current_price + price_range
            
            bids = [(float(p), float(q)) for p, q in depth['bids'] 
                    if price_min <= float(p) <= price_max]
            asks = [(float(p), float(q)) for p, q in depth['asks'] 
                    if price_min <= float(p) <= price_max]
            
            bid_vol = sum(q for _, q in bids)
            ask_vol = sum(q for _, q in asks)
            bid_cnt = len(bids)
            ask_cnt = len(asks)
            
            vol_ratio = bid_vol / ask_vol if ask_vol else float('inf')
            cnt_ratio = bid_cnt / ask_cnt if ask_cnt else float('inf')
            spread = asks[0][0] - bids[0][0] if asks and bids else 0
            
            # Calculate technical indicators
            rsi_5m = calculate_rsi(klines_5m)
            ma20_5m = calculate_ma(klines_5m, 20)
            ma50_15m = calculate_ma(klines_15m, 50)
            
            # Create enhanced market state
            return MarketState(
                timestamp=datetime.utcnow(),
                current_price=current_price,
                vol_ratio=vol_ratio,
                cnt_ratio=cnt_ratio,
                spread=spread,
                bid_vol=bid_vol,
                ask_vol=ask_vol,
                bid_cnt=bid_cnt,
                ask_cnt=ask_cnt,
                rsi_5m=rsi_5m,
                ma20_5m=ma20_5m,
                ma50_15m=ma50_15m,
                orderbook=depth,  # Store full orderbook for liquidity calculation
                long_short_ratio=self._calculate_long_short_ratio(klines_5m),
                trend_strength=self._calculate_trend_strength(klines_5m),
                liquidity_score=self._calculate_liquidity_score(depth)
            )
            
        except Exception as e:
            print(f"Error getting market state: {str(e)}")
            return None