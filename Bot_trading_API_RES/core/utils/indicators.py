"""
Technical indicators calculation module
"""

from typing import List, Dict, Optional
import numpy as np

def calculate_rsi(closes: List[float], period: int = 14) -> float:
    """
    Calculate Relative Strength Index
    
    Parameters:
    -----------
    closes : List[float]
        List of closing prices
    period : int
        RSI period
        
    Returns:
    --------
    float
        RSI value
    """
    try:
        if len(closes) < period + 1:
            return 50.0

        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
        
    except Exception:
        return 50.0

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

def calculate_delta(klines: List) -> float:
    """
    Calculate volume delta
    
    Parameters:
    -----------
    klines : List
        List of klines data
        
    Returns:
    --------
    float
        Delta percentage
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

def calculate_poc(timeframe_klines: List[List]) -> Optional[float]:
    """
    Calculate Point of Control
    
    Parameters:
    -----------
    timeframe_klines : List[List]
        List of klines data from multiple timeframes
        
    Returns:
    --------
    float or None
        POC value
    """
    try:
        all_prices = []
        for klines in timeframe_klines:
            prices = [(float(k[2]) + float(k[3])) / 2 for k in klines]
            all_prices.extend(prices)
            
        return float(np.median(all_prices)) if all_prices else None
        
    except Exception:
        return None

def calculate_volume_profile(klines: List) -> Dict:
    """
    Calculate volume profile
    
    Parameters:
    -----------
    klines : List
        List of klines data
        
    Returns:
    --------
    Dict
        Volume profile data
    """
    try:
        prices = [float(k[4]) for k in klines]  # Close prices
        volumes = [float(k[5]) for k in klines]  # Volumes
        
        return {
            "price_levels": prices,
            "volumes": volumes,
            "total_volume": sum(volumes),
            "vwap": sum(p * v for p, v in zip(prices, volumes)) / sum(volumes)
        }
        
    except Exception:
        return {
            "price_levels": [],
            "volumes": [],
            "total_volume": 0,
            "vwap": 0
        }
