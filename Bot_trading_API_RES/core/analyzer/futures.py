"""
Futures market analyzer component
Handles futures market analysis and signal generation
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from binance import Client

from ..models import SignalData, VolumeZone
from ..utils.calculations import calculate_delta, calculate_ma, calculate_rsi, calculate_poc
from .market_trend import MarketTrendAnalyzer
from ...config.settings import get_config

class FuturesAnalyzer:
    def __init__(self, client: Client, user_login: str = "Anhbaza"):
        self.client = client
        self.user_login = user_login
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.TREND_MIN_STRENGTH = get_config('TREND_MIN_STRENGTH') or 1.0
        self.TREND_IDEAL_STRENGTH = get_config('TREND_IDEAL_STRENGTH') or 1.5
        self.ACCUMULATION_RSI_MAX = get_config('RSI_OVERBOUGHT') or 65
        self.DISTRIBUTION_RSI_MIN = get_config('RSI_OVERSOLD') or 35
        self.TIMEFRAMES = get_config('TIMEFRAMES') or ['3m', '5m', '15m']
        self.PRIMARY_TIMEFRAME = get_config('PRIMARY_TIMEFRAME') or '5m'
        
        # Trading parameters
        self.MIN_24H_VOLUME = get_config('MIN_24H_VOLUME') or 300_000
        self.MAX_SPREAD = get_config('MAX_SPREAD') or 0.003
        self.MAX_FUNDING_RATE = get_config('MAX_FUNDING_RATE') or 0.001
        self.MIN_OI = get_config('MIN_OI') or 200_000
        self.MAX_OI = get_config('MAX_OI') or 200_000_000_000
        
        # Volume Zones parameters
        self.N_SCAN = get_config('PRICE_RANGE_PERCENT') or 0.02
        self.MIN_ORDER_COUNT = get_config('MIN_ORDER_COUNT') or 1
        self.MIN_LS_RATIO = get_config('MIN_LS_RATIO') or 1.3
        self.MAX_LS_RATIO = get_config('MAX_LS_RATIO') or 10.0
        self.RATE_LIMIT_DELAY = get_config('RATE_LIMIT_DELAY') or 0.5

        # Initialize trend analyzer
        self.trend_analyzer = MarketTrendAnalyzer(
            api_key=client.API_KEY,
            api_secret=client.API_SECRET,
            symbol="",
            depth_limit=200,
            price_range_percent=0.2,
            vol_threshold=1.2,
            cnt_threshold=1.2
        )

    def log(self, message: str, level: str = "info"):
        """Log with user login prefix"""
        log_message = f"{self.user_login} | {message}"
        
        if level == "error":
            self.logger.error(log_message)
        elif level == "warning":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

    async def quick_pre_filter(self, symbol: str) -> bool:
        """Quick check for basic conditions"""
        try:
            self.log(f"{symbol}: Starting quick pre-filter...")
            
            # Get 24h ticker
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(
                None,
                lambda: self.client.futures_ticker(symbol=symbol)
            )
            
            volume_24h = float(ticker['volume']) * float(ticker['lastPrice'])
            if volume_24h < self.MIN_24H_VOLUME:
                self.log(f"{symbol}: ❌ Failed volume check - ${volume_24h:,.2f}")
                return False
                
            # Check trend
            self.trend_analyzer.symbol = symbol
            trend = await loop.run_in_executor(None, self.trend_analyzer.analyze_trend)
            
            if not trend or trend.type == 'NEUTRAL':
                self.log(f"{symbol}: ❌ Failed trend check")
                return False
                
            if trend.strength < self.TREND_MIN_STRENGTH:
                self.log(f"{symbol}: ❌ Failed trend strength check")
                return False
                
            return True
            
        except Exception as e:
            self.log(f"Error in quick pre-filter for {symbol}: {str(e)}", "error")
            return False

    async def analyze_entry_conditions(self, symbol: str) -> Optional[SignalData]:
        """Analyze entry conditions for a symbol"""
        try:
            self.log(f"{symbol}: Analyzing entry conditions...")
            
            # Get data
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(None, lambda: self.client.futures_klines(symbol=symbol, interval=tf, limit=100))
                for tf in self.TIMEFRAMES
            ]
            tasks.append(loop.run_in_executor(None, lambda: self.client.futures_order_book(symbol=symbol, limit=100)))
            
            klines_data = await asyncio.gather(*tasks)
            orderbook = klines_data[-1]
            klines_3m, klines_5m, klines_15m = klines_data[:-1]

            # Calculate indicators
            deltas = [calculate_delta(k) for k in [klines_3m, klines_5m, klines_15m]]
            ma20 = calculate_ma(klines_5m, 20)
            ma50 = calculate_ma(klines_15m, 50)
            rsi_5m = calculate_rsi(klines_5m)
            rsi_15m = calculate_rsi(klines_15m)

            # Log indicators
            self.log(f"{symbol} Indicators:")
            self.log(f"- Delta (3m/5m/15m): {'/'.join(f'{d:.2f}' for d in deltas)}")
            self.log(f"- MA20_5m/MA50_15m: {ma20:.2f}/{ma50:.2f}")
            self.log(f"- RSI (5m/15m): {rsi_5m:.2f}/{rsi_15m:.2f}")

            # Calculate POC and volume zones
            poc = calculate_poc([klines_3m, klines_5m, klines_15m])
            if poc is None:
                self.log(f"{symbol}: ❌ Cannot calculate POC")
                return None

            # Get current price
            best_ask = float(orderbook['asks'][0][0])
            best_bid = float(orderbook['bids'][0][0])
            mid_price = (best_ask + best_bid) / 2

            # Get trend analysis
            trend = await loop.run_in_executor(None, self.trend_analyzer.analyze_trend)
            if not trend:
                self.log(f"{symbol}: ❌ Cannot determine trend")
                return None

            # Check conditions and generate signals
            signal = await self._check_trading_conditions(
                symbol=symbol,
                trend=trend,
                mid_price=mid_price,
                poc=poc,
                deltas=deltas,
                ma20=ma20,
                ma50=ma50,
                rsi_5m=rsi_5m,
                rsi_15m=rsi_15m,
                orderbook=orderbook
            )

            return signal

        except Exception as e:
            self.log(f"Error analyzing {symbol}: {str(e)}", "error")
            return None

    async def _check_trading_conditions(self, **kwargs) -> Optional[SignalData]:
        """Check trading conditions and generate signal"""
        # Implementation of trading conditions check
        # This would include the LONG and SHORT condition checks
        # from the previous implementation
        pass

    def generate_signal(self, **kwargs) -> SignalData:
        """Generate trading signal with full information"""
        # Implementation of signal generation
        # This would include the signal generation logic
        # from the previous implementation
        pass
