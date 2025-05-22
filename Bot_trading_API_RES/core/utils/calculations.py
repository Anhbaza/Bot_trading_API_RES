"""
Technical analysis calculations for Bot Trading API REST
Provides functions for market analysis and indicators
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime

def calculate_delta(klines: List) -> float:
    """
    Calculate delta (buy/sell volume ratio) from klines
    
    Parameters:
    -----------
    klines : List
        List of klines data from Binance API
        
    Returns:
    --------
    float
        Delta value (-100 to 100)
    """
    try:
        if not klines or len(klines) < 2:
            return 0
            
        buy_volume = sum(float(k[5]) if float(k[4]) >= float(k[1]) else 0 for k in klines)
        sell_volume = sum(float(k[5]) if float(k[4]) < float(k[1]) else 0 for k in klines)
        
        total_volume = buy_volume + sell_volume
        return (buy_volume - sell_volume) / total_volume * 100 if total_volume > 0 else 0
        
    except Exception:
        return 0

def calculate_ma(klines: List, period: int) -> float:
    """
    Calculate Moving Average
    
    Parameters:
    -----------
    klines : List
        List of klines data
    period : int
        MA period
        
    Returns:
    --------
    float
        MA value
    """
    try:
        if len(klines) < period:
            return 0
        closes = [float(k[4]) for k in klines[-period:]]
        return sum(closes) / period
    except Exception:
        return 0

def calculate_rsi(klines: List, period: int = 14) -> float:
    """
    Calculate Relative Strength Index
    
    Parameters:
    -----------
    klines : List
        List of klines data
    period : int
        RSI period (default: 14)
        
    Returns:
    --------
    float
        RSI value (0-100)
    """
    try:
        if len(klines) < period + 1:
            return 50
            
        closes = [float(k[4]) for k in klines]
        deltas = np.diff(closes)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
        
    except Exception:
        return 50

def calculate_poc(timeframe_klines: List[List]) -> Optional[float]:
    """
    Calculate Point of Control from multiple timeframe klines
    
    Parameters:
    -----------
    timeframe_klines : List[List]
        List of klines data from multiple timeframes
        
    Returns:
    --------
    float or None
        POC price level
    """
    try:
        all_prices = []
        for klines in timeframe_klines:
            prices = [(float(k[2]) + float(k[3])) / 2 for k in klines]
            all_prices.extend(prices)
            
        return float(np.median(all_prices)) if all_prices else None
        
    except Exception:
        return None

def calculate_volume_profile(
    klines: List,
    price_levels: int = 100,
    volume_threshold: float = 0.1
) -> Dict[float, float]:
    """
    Calculate Volume Profile
    
    Parameters:
    -----------
    klines : List
        List of klines data
    price_levels : int
        Number of price levels to analyze
    volume_threshold : float
        Minimum volume ratio to consider
        
    Returns:
    --------
    Dict[float, float]
        Price levels and their volume
    """
    try:
        if not klines:
            return {}
            
        # Extract prices and volumes
        prices = [(float(k[2]) + float(k[3])) / 2 for k in klines]
        volumes = [float(k[5]) for k in klines]
        
        # Create price levels
        min_price = min(prices)
        max_price = max(prices)
        level_size = (max_price - min_price) / price_levels
        
        # Calculate volume for each level
        profile = {}
        for price, volume in zip(prices, volumes):
            level = min_price + level_size * int((price - min_price) / level_size)
            profile[level] = profile.get(level, 0) + volume
            
        # Filter by threshold
        total_volume = sum(profile.values())
        threshold_volume = total_volume * volume_threshold
        
        return {k: v for k, v in profile.items() if v >= threshold_volume}
        
    except Exception:
        return {}

def calculate_support_resistance(
    klines: List,
    num_levels: int = 5,
    window_size: int = 20
) -> Tuple[List[float], List[float]]:
    """
    Calculate Support and Resistance levels
    
    Parameters:
    -----------
    klines : List
        List of klines data
    num_levels : int
        Number of levels to identify
    window_size : int
        Window size for peak detection
        
    Returns:
    --------
    Tuple[List[float], List[float]]
        Support and resistance levels
    """
    try:
        if len(klines) < window_size:
            return [], []
            
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        
        resistance_levels = []
        support_levels = []
        
        # Find peaks and troughs
        for i in range(window_size, len(klines) - window_size):
            window_highs = highs[i-window_size:i+window_size]
            window_lows = lows[i-window_size:i+window_size]
            
            if highs[i] == max(window_highs):
                resistance_levels.append(highs[i])
            if lows[i] == min(window_lows):
                support_levels.append(lows[i])
                
        # Sort and get top levels
        resistance_levels = sorted(set(resistance_levels), reverse=True)[:num_levels]
        support_levels = sorted(set(support_levels))[:num_levels]
        
        return support_levels, resistance_levels
        
    except Exception:
        return [], []

def calculate_risk_reward_ratio(
    entry: float,
    stop_loss: float,
    take_profit: float,
    position_type: str
) -> float:
    """
    Calculate Risk/Reward ratio
    
    Parameters:
    -----------
    entry : float
        Entry price
    stop_loss : float
        Stop loss price
    take_profit : float
        Take profit price
    position_type : str
        'LONG' or 'SHORT'
        
    Returns:
    --------
    float
        Risk/Reward ratio
    """
    try:
        if position_type == 'LONG':
            risk = abs(entry - stop_loss)
            reward = abs(take_profit - entry)
        else:  # SHORT
            risk = abs(stop_loss - entry)
            reward = abs(entry - take_profit)
            
        return reward / risk if risk > 0 else 0
        
    except Exception:
        return 0
