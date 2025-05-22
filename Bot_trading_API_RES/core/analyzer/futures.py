"""
Futures market analyzer component
Handles futures market analysis and signal generation
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from binance import Client

from config.settings import get_config  # Sửa lại import
from core.models import SignalData, VolumeZone
from core.utils.calculations import calculate_delta, calculate_ma, calculate_rsi, calculate_poc
from .market_trend import MarketTrendAnalyzer

class FuturesAnalyzer:
    # Thay đổi phần khởi tạo trend_analyzer trong __init__
 def __init__(self, client: Client, user_login: str = "", settings: Dict = None):
    """
    Initialize FuturesAnalyzer
    
    Parameters
    ----------
    client : Client
        Binance API client instance
    user_login : str, optional
        User login name for logging
    settings : Dict, optional
        Configuration settings
    """
    self.client = client
    self.user_login = user_login
    self.logger = logging.getLogger(__name__)
    
    # Load settings
    settings = settings or {}
    
    # Trend thresholds
    self.TREND_MIN_STRENGTH = settings.get('TREND_MIN_STRENGTH', 1.0)
    self.TREND_IDEAL_STRENGTH = settings.get('TREND_IDEAL_STRENGTH', 1.5)

    # RSI thresholds
    self.ACCUMULATION_RSI_MAX = 65
    self.DISTRIBUTION_RSI_MIN = 35
    
    # Timeframes 
    self.TIMEFRAMES = ['3m', '5m', '15m']
    self.PRIMARY_TIMEFRAME = '5m'
    
    # Pre-filter parameters
    self.MIN_24H_VOLUME = settings.get('MIN_24H_VOLUME', 300_000)
    self.MAX_SPREAD = settings.get('MAX_SPREAD', 0.003)
    self.MAX_FUNDING_RATE = settings.get('MAX_FUNDING_RATE', 0.001)
    self.MIN_OI = settings.get('MIN_OI', 200_000)
    self.MAX_OI = settings.get('MAX_OI', 200_000_000_000)
    
    # Volume Zones parameters  
    self.N_SCAN = 0.02
    self.MIN_ORDER_COUNT = 1
    
    # Long/Short ratio limits
    self.MIN_LS_RATIO = settings.get('MIN_LS_RATIO', 1.3)
    self.MAX_LS_RATIO = settings.get('MAX_LS_RATIO', 10.0)
    self.RATE_LIMIT_DELAY = settings.get('RATE_LIMIT_DELAY', 0.5)
    
    # Watched pairs
    self.WATCHED_PAIRS = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT',
        'DOGEUSDT', 'MATICUSDT', 'SOLUSDT', 'DOTUSDT', 'AVAXUSDT'
    ]
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
        try:
            symbol = kwargs.get('symbol')
            trend = kwargs.get('trend')
            mid_price = kwargs.get('mid_price')
            poc = kwargs.get('poc')
            deltas = kwargs.get('deltas')
            ma20 = kwargs.get('ma20')
            ma50 = kwargs.get('ma50')
            rsi_5m = kwargs.get('rsi_5m')
            rsi_15m = kwargs.get('rsi_15m')
            orderbook = kwargs.get('orderbook')

            if not all([symbol, trend, mid_price, poc, deltas, ma20, ma50, rsi_5m, rsi_15m, orderbook]):
                return None

            # LONG conditions
            if (trend.type == 'ACCUMULATION' and
                all(d > 0 for d in deltas) and
                mid_price > ma20 > ma50 and
                rsi_5m < self.ACCUMULATION_RSI_MAX):

                return self.generate_signal(
                    symbol=symbol,
                    signal_type='LONG',
                    entry=mid_price,
                    stop_loss=min(poc * 0.995, ma20),
                    take_profit=poc * 1.015,
                    reason="Accumulation trend with positive momentum",
                    confidence=trend.confidence
                )

            # SHORT conditions    
            elif (trend.type == 'DISTRIBUTION' and
                  all(d < 0 for d in deltas) and
                  mid_price < ma20 < ma50 and
                  rsi_5m > self.DISTRIBUTION_RSI_MIN):

                return self.generate_signal(
                    symbol=symbol,
                    signal_type='SHORT',
                    entry=mid_price,
                    stop_loss=max(poc * 1.005, ma20),
                    take_profit=poc * 0.985,
                    reason="Distribution trend with negative momentum",
                    confidence=trend.confidence
                )

            return None

        except Exception as e:
            self.log(f"Error checking conditions for {kwargs.get('symbol', 'Unknown')}: {str(e)}", "error")
            return None

    def generate_signal(self, **kwargs) -> SignalData:
        """Generate trading signal with full information"""
        return SignalData(
            symbol=kwargs['symbol'],
            signal_type=kwargs['signal_type'],
            entry=kwargs['entry'],
            stop_loss=kwargs['stop_loss'],
            take_profit=kwargs['take_profit'],
            reason=kwargs['reason'],
            timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            confidence=kwargs.get('confidence', 0.0)
        )