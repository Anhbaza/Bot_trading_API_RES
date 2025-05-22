"""
Validation utilities for Bot Trading API REST
Provides functions for validating trading parameters and data
"""

from typing import Dict, Optional, Union, Tuple
import re

def validate_price(
    price: float,
    min_price: float = 0,
    max_price: Optional[float] = None
) -> bool:
    """
    Validate price value
    
    Parameters:
    -----------
    price : float
        Price to validate
    min_price : float
        Minimum allowed price
    max_price : float, optional
        Maximum allowed price
        
    Returns:
    --------
    bool
        True if valid, False otherwise
    """
    try:
        if price <= min_price:
            return False
        if max_price and price >= max_price:
            return False
        return True
    except Exception:
        return False

def validate_quantity(
    quantity: float,
    min_qty: float,
    max_qty: float,
    step_size: float
) -> bool:
    """
    Validate quantity value
    
    Parameters:
    -----------
    quantity : float
        Quantity to validate
    min_qty : float
        Minimum allowed quantity
    max_qty : float
        Maximum allowed quantity
    step_size : float
        Quantity step size
        
    Returns:
    --------
    bool
        True if valid, False otherwise
    """
    try:
        if quantity < min_qty or quantity > max_qty:
            return False
            
        # Check if quantity is multiple of step_size
        remainder = quantity % step_size
        return abs(remainder) < 1e-8  # Account for floating point precision
        
    except Exception:
        return False

def validate_symbol(symbol: str) -> bool:
    """
    Validate trading symbol format
    
    Parameters:
    -----------
    symbol : str
        Trading symbol to validate
        
    Returns:
    --------
    bool
        True if valid, False otherwise
    """
    try:
        # Basic symbol format validation
        pattern = r'^[A-Z0-9]{2,20}$'
        return bool(re.match(pattern, symbol))
    except Exception:
        return False

def validate_timeframe(timeframe: str) -> bool:
    """
    Validate timeframe format
    
    Parameters:
    -----------
    timeframe : str
        Timeframe to validate (e.g., '1m', '1h', '1d')
        
    Returns:
    --------
    bool
        True if valid, False otherwise
    """
    try:
        valid_timeframes = {
            'm': range(1, 60),  # 1-59 minutes
            'h': range(1, 24),  # 1-23 hours
            'd': range(1, 31),  # 1-30 days
            'w': range(1, 53),  # 1-52 weeks
            'M': range(1, 13)   # 1-12 months
        }
        
        if len(timeframe) < 2:
            return False
            
        value = int(timeframe[:-1])
        unit = timeframe[-1]
        
        return unit in valid_timeframes and value in valid_timeframes[unit]
        
    except Exception:
        return False

def validate_trade_parameters(
    params: Dict[str, Union[str, float, int]]
) -> Tuple[bool, Optional[str]]:
    """
    Validate trading parameters
    
    Parameters:
    -----------
    params : Dict
        Trading parameters to validate
        
    Returns:
    --------
    Tuple[bool, Optional[str]]
        (is_valid, error_message)
    """
    try:
        required_fields = {
            'symbol': str,
            'side': str,
            'type': str,
            'quantity': float,
            'leverage': int
        }
        
        # Check required fields
        for field, field_type in required_fields.items():
            if field not in params:
                return False, f"Missing required field: {field}"
            if not isinstance(params[field], field_type):
                return False, f"Invalid type for {field}"
                
        # Validate specific fields
        if params['side'] not in ['BUY', 'SELL']:
            return False, "Invalid side"
            
        if params['type'] not in ['MARKET', 'LIMIT']:
            return False, "Invalid order type"
            
        if params['quantity'] <= 0:
            return False, "Invalid quantity"
            
        if params['leverage'] < 1 or params['leverage'] > 125:
            return False, "Invalid leverage"
            
        # Additional validations for LIMIT orders
        if params['type'] == 'LIMIT':
            if 'price' not in params:
                return False, "Missing price for LIMIT order"
            if params['price'] <= 0:
                return False, "Invalid price"
                
        return True, None
        
    except Exception as e:
        return False, str(e)