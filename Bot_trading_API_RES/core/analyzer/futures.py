"""
Futures market analyzer component
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
import numpy as np
from binance import Client
from core.models import SignalData, VolumeZone

class FuturesAnalyzer:
    def __init__(self, client: Client, user_login: str = "", settings: Dict = None):
        """Initialize the analyzer"""
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

    def log(self, message: str, level: str = "info"):
        """Log with user prefix"""
        log_message = f"{self.user_login} | {message}" if self.user_login else message
        if level == "error":
            self.logger.error(log_message)
        elif level == "warning":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

    def quick_pre_filter(self, symbol: str) -> bool:
        """Quick pre-filter check"""
        try:
            self.log(f"{symbol}: Quick pre-filter check...")
            
            # Get 24h ticker
            ticker = self.client.futures_ticker(symbol=symbol)
            volume_24h = float(ticker['volume']) * float(ticker['lastPrice'])
            
            if volume_24h < self.MIN_24H_VOLUME:
                self.log(
                    f"{symbol}: Failed volume check - ${volume_24h:,.2f} < ${self.MIN_24H_VOLUME:,.2f}",
                    "warning"
                )
                return False
                
            # Get order book
            orderbook = self.client.futures_order_book(symbol=symbol, limit=5)
            best_ask = float(orderbook['asks'][0][0])
            best_bid = float(orderbook['bids'][0][0])
            spread = (best_ask - best_bid) / best_bid
            
            if spread > self.MAX_SPREAD:
                self.log(
                    f"{symbol}: Failed spread check - {spread*100:.3f}% > {self.MAX_SPREAD*100:.3f}%",
                    "warning"
                )
                return False
                
            # Get funding rate
            funding = self.client.futures_funding_rate(symbol=symbol, limit=1)
            funding_rate = float(funding[0]['fundingRate'])
            
            if abs(funding_rate) > self.MAX_FUNDING_RATE:
                self.log(
                    f"{symbol}: Failed funding rate check - {abs(funding_rate)*100:.3f}% > {self.MAX_FUNDING_RATE*100:.3f}%",
                    "warning"
                )
                return False
                
            self.log(f"{symbol}: Passed quick pre-filter")
            return True
            
        except Exception as e:
            self.log(f"Error in quick pre-filter for {symbol}: {str(e)}", "error")
            return False

    async def analyze_entry_conditions(self, symbol: str) -> Optional[SignalData]:
        """Analyze entry conditions"""
        try:
            self.log(f"{symbol}: Analyzing entry conditions...")
            
            # Get data from multiple timeframes
            tasks = [
                self._get_klines(symbol, tf) for tf in self.TIMEFRAMES
            ]
            klines_data = await asyncio.gather(*tasks)
            
            if not all(klines_data):
                self.log(f"{symbol}: Failed to get klines data", "error")
                return None
                
            klines_3m, klines_5m, klines_15m = klines_data
            
            # Calculate indicators
            rsi_5m = self._calculate_rsi(klines_5m)
            rsi_15m = self._calculate_rsi(klines_15m)
            ma20_5m = self._calculate_ma(klines_5m, 20)
            ma50_15m = self._calculate_ma(klines_15m, 50)
            
            # Get current price
            current_price = float(klines_5m[-1][4])
            
            # Calculate volume profile
            volume_zones = self._analyze_volume_zones(symbol)
            if not volume_zones:
                return None
                
            # Check LONG conditions
            if (current_price > ma20_5m > ma50_15m and 
                rsi_5m < self.ACCUMULATION_RSI_MAX and 
                rsi_15m < self.ACCUMULATION_RSI_MAX):
                
                return self._generate_signal(
                    symbol=symbol,
                    signal_type='LONG',
                    entry_price=current_price,
                    rsi_5m=rsi_5m,
                    rsi_15m=rsi_15m,
                    volume_zones=volume_zones
                )
                
            # Check SHORT conditions
            elif (current_price < ma20_5m < ma50_15m and
                  rsi_5m > self.DISTRIBUTION_RSI_MIN and
                  rsi_15m > self.DISTRIBUTION_RSI_MIN):
                  
                return self._generate_signal(
                    symbol=symbol,
                    signal_type='SHORT',
                    entry_price=current_price,
                    rsi_5m=rsi_5m,
                    rsi_15m=rsi_15m,
                    volume_zones=volume_zones
                )
                
            return None
            
        except Exception as e:
            self.log(f"Error analyzing {symbol}: {str(e)}", "error")
            return None

    async def _get_klines(self, symbol: str, interval: str) -> Optional[List]:
        """Get klines data"""
        try:
            return self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=100
            )
        except Exception as e:
            self.log(f"Error getting klines for {symbol}: {str(e)}", "error")
            return None

    def _calculate_rsi(self, klines: List, period: int = 14) -> float:
        """Calculate RSI"""
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

    def _calculate_ma(self, klines: List, period: int) -> float:
        """Calculate Moving Average"""
        try:
            if len(klines) < period:
                return 0
            closes = [float(k[4]) for k in klines[-period:]]
            return sum(closes) / period
        except Exception:
            return 0

    def _analyze_volume_zones(self, symbol: str) -> Dict[float, VolumeZone]:
        """Analyze volume zones"""
        try:
            orderbook = self.client.futures_order_book(symbol=symbol, limit=100)
            zones = {}
            
            for price, qty in orderbook['asks']:
                price = float(price)
                if price not in zones:
                    zones[price] = VolumeZone(price, 0, float(qty), 1)
                else:
                    zones[price].short_volume += float(qty)
                    zones[price].order_count += 1
                    
            for price, qty in orderbook['bids']:
                price = float(price)
                if price not in zones:
                    zones[price] = VolumeZone(price, float(qty), 0, 1)
                else:
                    zones[price].long_volume += float(qty)
                    zones[price].order_count += 1
                    
            return {p: z for p, z in zones.items() if z.order_count >= self.MIN_ORDER_COUNT}
            
        except Exception as e:
            self.log(f"Error analyzing volume zones for {symbol}: {str(e)}", "error")
            return {}

    def _generate_signal(
        self,
        symbol: str,
        signal_type: str,
        entry_price: float,
        rsi_5m: float,
        rsi_15m: float,
        volume_zones: Dict[float, VolumeZone]
    ) -> Optional[SignalData]:
        """Generate trading signal"""
        try:
            # Calculate ATR for stop loss and take profit
            atr = self._calculate_atr(symbol)
            
            if signal_type == 'LONG':
                stop_loss = entry_price * (1 - atr * 1.5)
                take_profit = entry_price * (1 + atr * 3.0)
                emoji = "💹"
            else:  # SHORT
                stop_loss = entry_price * (1 + atr * 1.5)
                take_profit = entry_price * (1 - atr * 3.0)
                emoji = "📉"

            # Calculate volume ratio
            volume_ratio = self._calculate_volume_ratio(volume_zones)
            
            # Calculate signal confidence
            confidence = self._calculate_signal_confidence(
                signal_type=signal_type,
                rsi_5m=rsi_5m,
                rsi_15m=rsi_15m,
                volume_ratio=volume_ratio
            )

            reason = (
                f"{emoji} {signal_type} Signal\n\n"
                f"Technical Analysis:\n"
                f"• RSI(5m/15m): {rsi_5m:.1f}/{rsi_15m:.1f}\n"
                f"• Volume Ratio: {volume_ratio:.2f}\n"
                f"• Orders: {sum(vz.order_count for vz in volume_zones.values())}\n\n"
                f"Risk Management:\n"
                f"• Stop Loss: {abs((stop_loss - entry_price) / entry_price * 100):.2f}%\n"
                f"• Take Profit: {abs((take_profit - entry_price) / entry_price * 100):.2f}%\n"
                f"• Risk/Reward: {abs((take_profit - entry_price) / (stop_loss - entry_price)):.2f}\n"
                f"• Confidence: {confidence:.2f}"
            )

            return SignalData(
                symbol=symbol,
                signal_type=signal_type,
                entry=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=reason,
                timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                confidence=confidence
            )

        except Exception as e:
            self.log(f"Error generating signal for {symbol}: {str(e)}", "error")
            return None

    def _calculate_atr(self, symbol: str, period: int = 14) -> float:
        """Calculate ATR"""
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=self.PRIMARY_TIMEFRAME,
                limit=period + 1
            )
            
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            closes = [float(k[4]) for k in klines]
            
            tr = [max(highs[i] - lows[i],
                     abs(highs[i] - closes[i-1]),
                     abs(lows[i] - closes[i-1]))
                  for i in range(1, len(klines))]
                  
            atr = sum(tr) / len(tr)
            return atr / closes[-1]  # Return as percentage
            
        except Exception:
            return 0.02  # Default to 2%

    def _calculate_volume_ratio(self, volume_zones: Dict[float, VolumeZone]) -> float:
        """Calculate volume ratio"""
        try:
            total_long = sum(vz.long_volume for vz in volume_zones.values())
            total_short = sum(vz.short_volume for vz in volume_zones.values())
            return total_long / max(total_short, 0.000001)
        except Exception:
            return 1.0

    def _calculate_signal_confidence(
        self,
        signal_type: str,
        rsi_5m: float,
        rsi_15m: float,
        volume_ratio: float
    ) -> float:
        """Calculate signal confidence"""
        try:
            confidence = 0.5  # Base confidence
            
            # RSI confidence
            if signal_type == 'LONG':
                rsi_conf = (self.ACCUMULATION_RSI_MAX - max(rsi_5m, rsi_15m)) / self.ACCUMULATION_RSI_MAX
            else:
                rsi_conf = (min(rsi_5m, rsi_15m) - self.DISTRIBUTION_RSI_MIN) / (100 - self.DISTRIBUTION_RSI_MIN)
                
            confidence += rsi_conf * 0.25
            
            # Volume ratio confidence
            vol_conf = min((volume_ratio / self.MAX_LS_RATIO), 1.0) if signal_type == 'LONG' else \
                      min((1/volume_ratio / self.MAX_LS_RATIO), 1.0)
            confidence += vol_conf * 0.25
            
            return min(max(confidence, 0.0), 0.95)
            
        except Exception:
            return 0.5