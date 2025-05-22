"""
Binance API client service for Bot Trading API REST
Handles all interactions with Binance's API
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from binance import Client, AsyncClient
from binance.exceptions import BinanceAPIException

class BinanceClient:
    def __init__(self, api_key: str = "", api_secret: str = ""):
        """
        Initialize Binance client
        
        Parameters:
        -----------
        api_key : str
            Binance API key
        api_secret : str
            Binance API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = Client(api_key, api_secret)
        self.logger = logging.getLogger(__name__)
        self.last_api_call = datetime.utcnow()
        self.RATE_LIMIT_DELAY = 0.1  # seconds between API calls

      # Add health check method
    async def check_health(self) -> bool:
        """Check API connection health"""
        try:
            await self._handle_rate_limit()
            await self.async_client.ping()
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False
    async def initialize_async_client(self):
        """Initialize async client"""
        self.async_client = await AsyncClient.create(self.api_key, self.api_secret)

    async def close_async_client(self):
        """Close async client"""
        await self.async_client.close_connection()

    async def _handle_rate_limit(self):
        """Handle API rate limiting"""
        now = datetime.utcnow()
        elapsed = (now - self.last_api_call).total_seconds()
        if elapsed < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_api_call = now

    async def get_futures_symbols(self) -> List[str]:
        """
        Get list of available futures symbols
        
        Returns:
        --------
        List[str]
            List of trading symbols
        """
        try:
            await self._handle_rate_limit()
            exchange_info = await self.async_client.futures_exchange_info()
            return [s['symbol'] for s in exchange_info['symbols'] if s['status'] == 'TRADING']
        except Exception as e:
            self.logger.error(f"Error getting futures symbols: {str(e)}")
            return []

    async def get_futures_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100
    ) -> List[List]:
        """
        Get futures klines/candlestick data
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        interval : str
            Kline interval
        limit : int
            Number of klines to get
            
        Returns:
        --------
        List[List]
            Klines data
        """
        try:
            await self._handle_rate_limit()
            return await self.async_client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
        except Exception as e:
            self.logger.error(f"Error getting klines for {symbol}: {str(e)}")
            return []

    async def get_futures_orderbook(
        self,
        symbol: str,
        limit: int = 100
    ) -> Dict:
        """
        Get futures order book
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        limit : int
            Depth of order book
            
        Returns:
        --------
        Dict
            Order book data
        """
        try:
            await self._handle_rate_limit()
            return await self.async_client.futures_order_book(
                symbol=symbol,
                limit=limit
            )
        except Exception as e:
            self.logger.error(f"Error getting orderbook for {symbol}: {str(e)}")
            return {'bids': [], 'asks': []}

    async def create_futures_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        **kwargs
    ) -> Dict:
        """
        Create futures order
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        side : str
            Order side (BUY/SELL)
        order_type : str
            Order type (MARKET/LIMIT/STOP/TAKE_PROFIT)
        quantity : float
            Order quantity
        price : float, optional
            Order price for limit orders
        stop_price : float, optional
            Stop price for stop orders
            
        Returns:
        --------
        Dict
            Order response
        """
        try:
            await self._handle_rate_limit()
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
                **kwargs
            }
            
            if price:
                params['price'] = price
            if stop_price:
                params['stopPrice'] = stop_price
                
            return await self.async_client.futures_create_order(**params)
            
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error creating order: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating order: {str(e)}")
            raise

    async def get_futures_position(self, symbol: str) -> Dict:
        """
        Get current futures position
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
            
        Returns:
        --------
        Dict
            Position information
        """
        try:
            await self._handle_rate_limit()
            positions = await self.async_client.futures_position_information(symbol=symbol)
            return positions[0] if positions else {}
        except Exception as e:
            self.logger.error(f"Error getting position for {symbol}: {str(e)}")
            return {}

    async def get_futures_account(self) -> Dict:
        """
        Get futures account information
        
        Returns:
        --------
        Dict
            Account information
        """
        try:
            await self._handle_rate_limit()
            return await self.async_client.futures_account()
        except Exception as e:
            self.logger.error(f"Error getting futures account: {str(e)}")
            return {}

    async def change_leverage(self, symbol: str, leverage: int) -> Dict:
        """
        Change leverage for symbol
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        leverage : int
            Leverage value (1-125)
            
        Returns:
        --------
        Dict
            Leverage update response
        """
        try:
            await self._handle_rate_limit()
            return await self.async_client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )
        except Exception as e:
            self.logger.error(f"Error changing leverage for {symbol}: {str(e)}")
            return {}
