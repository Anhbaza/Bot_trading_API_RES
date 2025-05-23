 #!/usr/bin/env python3
"""
Signal Processor Module
Author: Anhbaza01
Version: 1.0.0
Last Updated: 2025-05-23 19:15:05 UTC

This module handles trading signal processing including:
- Signal confidence calculation
- Trend analysis and change detection
- Signal updates and notifications
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from .constants import (
    RSI_PERIOD,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    MIN_RR_RATIO,
    VOLUME_RATIO_MIN
)

class SignalProcessor:
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize Signal Processor"""
        self.logger = logger or logging.getLogger(__name__)

    def calculate_confidence(self, signal: Dict[str, Any], klines: List[Dict]) -> float:
        """
        Calculate confidence score for a trading signal (0-100%)
        
        Parameters:
            signal (Dict[str, Any]): Trading signal data
            klines (List[Dict]): Historical price data
            
        Returns:
            float: Confidence score 0-100%
        """
        try:
            confidence = 0
            
            # 1. RSI Weight (30%)
            rsi = signal.get('rsi', 50)
            if signal['type'] == "LONG":
                rsi_score = (30 - rsi) / 30 * 30 if rsi <= 30 else 0
            else:
                rsi_score = (rsi - 70) / 30 * 30 if rsi >= 70 else 0
            confidence += rsi_score
            
            # 2. Volume Weight (30%)
            if len(klines) >= 20:
                current_volume = klines[-1]['volume']
                avg_volume = sum(k['volume'] for k in klines[-20:-1]) / 19
                volume_ratio = current_volume / avg_volume
                volume_score = min((volume_ratio - 1) * 30, 30)
                confidence += max(volume_score, 0)
            
            # 3. Price Action (20%)
            if len(klines) >= 3:
                current = klines[-1]
                prev1 = klines[-2]
                prev2 = klines[-3]
                
                # Check candle patterns
                if signal['type'] == "LONG":
                    # Bullish pattern
                    if (current['close'] > current['open'] and
                        current['close'] > prev1['high'] and
                        prev1['close'] < prev1['open']):
                        confidence += 20
                else:
                    # Bearish pattern
                    if (current['close'] < current['open'] and
                        current['close'] < prev1['low'] and
                        prev1['close'] > prev1['open']):
                        confidence += 20
            
            # 4. Risk-Reward Ratio (20%)
            entry = signal['entry']
            tp = signal['tp']
            sl = signal['sl']
            rr = abs((tp - entry) / (entry - sl))
            rr_score = min(rr * 10, 20)
            confidence += rr_score
            
            return round(confidence, 1)
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {str(e)}")
            return 0

    def analyze_trend(self, signal: Dict[str, Any], klines: List[Dict]) -> Dict[str, Any]:
        """
        Analyze current trend and detect changes
        
        Parameters:
            signal (Dict[str, Any]): Current active signal
            klines (List[Dict]): Historical price data
            
        Returns:
            Dict[str, Any]: Analysis result containing:
                - trend_changed (bool)
                - trend_reinforced (bool)
                - new_targets (Dict) if reinforced
        """
        try:
            if len(klines) < 50:
                return {
                    'trend_changed': False,
                    'trend_reinforced': False
                }
            
            # Get current data
            current_price = klines[-1]['close']
            closes = [k['close'] for k in klines]
            
            # Calculate indicators
            rsi = self._calculate_rsi(closes)
            ema20 = self._calculate_ema(closes, 20)
            ema50 = self._calculate_ema(closes, 50)
            
            signal_type = signal['type']
            result = {
                'trend_changed': False,
                'trend_reinforced': False,
                'new_targets': None
            }
            
            # Check trend change
            if signal_type == "LONG":
                if (rsi >= RSI_OVERBOUGHT or 
                    (ema20 < ema50 and current_price < ema20)):
                    result['trend_changed'] = True
                    return result
                    
            else:  # SHORT
                if (rsi <= RSI_OVERSOLD or 
                    (ema20 > ema50 and current_price > ema20)):
                    result['trend_changed'] = True
                    return result
            
            # Check trend reinforcement
            if signal_type == "LONG":
                if (rsi < 40 and ema20 > ema50 and
                    current_price > signal['entry']):
                    result['trend_reinforced'] = True
                    
            else:  # SHORT
                if (rsi > 60 and ema20 < ema50 and
                    current_price < signal['entry']):
                    result['trend_reinforced'] = True
            
            # Calculate new targets if trend reinforced
            if result['trend_reinforced']:
                atr = self._calculate_atr(klines)
                
                if signal_type == "LONG":
                    sl = current_price - (atr * 2)
                    tp = current_price + (atr * 2 * MIN_RR_RATIO)
                else:
                    sl = current_price + (atr * 2)
                    tp = current_price - (atr * 2 * MIN_RR_RATIO)
                
                result['new_targets'] = {
                    'tp': tp,
                    'sl': sl
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing trend: {str(e)}")
            return {
                'trend_changed': False,
                'trend_reinforced': False
            }
    def check_volume_signal(self, klines: List[Dict]) -> Optional[str]:
     """Check for volume breakout signal"""
     try:
        if len(klines) < 20:
            self.logger.info("Insufficient klines for volume analysis")
            return None
            
        # Get current candle data
        current = klines[-1]
        prev = klines[-2]
        
        # Calculate volume moving average
        volume_ma = sum(k['volume'] for k in klines[-20:-1]) / 19
        volume_change = current['volume'] / volume_ma
        
        self.logger.info(
            f"Volume analysis: Current = {current['volume']:.2f}, "
            f"MA = {volume_ma:.2f}, Ratio = {volume_change:.2f}x"
        )
        
        if volume_change >= VOLUME_RATIO_MIN:
            self.logger.info(f"Volume breakout detected ({volume_change:.2f}x)")
            
            # Calculate price changes
            price_change = (current['close'] - current['open']) / current['open'] * 100
            prev_change = (prev['close'] - prev['open']) / prev['open'] * 100
            
            self.logger.info(
                f"Price changes: Current = {price_change:+.2f}%, "
                f"Previous = {prev_change:+.2f}%"
            )
            
            # Check for trend continuation
            if (price_change > 0 and prev_change > 0 and 
                current['close'] > prev['close']):
                self.logger.info("Bullish continuation confirmed")
                return "LONG"
            elif (price_change < 0 and prev_change < 0 and 
                  current['close'] < prev['close']):
                self.logger.info("Bearish continuation confirmed")
                return "SHORT"
            else:
                self.logger.info("No clear trend continuation")
        else:
            self.logger.info(f"Volume below threshold ({volume_change:.2f}x < {VOLUME_RATIO_MIN}x)")
        
        return None
        
     except Exception as e:
        self.logger.error(f"Error checking volume signal: {str(e)}")
        return None
    def format_signal_message(self, signal: Dict[str, Any], msg_type: str = "NEW") -> str:
        """
        Format signal message for notifications
        
        Parameters:
            signal (Dict[str, Any]): Signal data
            msg_type (str): Message type (NEW/UPDATE/CLOSE)
            
        Returns:
            str: Formatted message
        """
        try:
            entry = signal['entry']
            tp = signal['tp']
            sl = signal['sl']
            rr = abs((tp - entry) / (entry - sl))
            
            if msg_type == "NEW":
                return f"""
🔔 <b>Tín hiệu giao dịch mới</b>
📊 {signal['symbol']}
📈 {signal['type']}
📉 RSI: {signal.get('rsi', 0):.1f}
💰 Giá vào: ${entry:.2f}
✅ Take Profit: ${tp:.2f}
❌ Stop Loss: ${sl:.2f}
⚖️ R:R = {rr:.1f}
📊 Độ tin cậy: {signal.get('confidence', 0)}%
⌚ {signal['time'].strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
            elif msg_type == "UPDATE":
                return f"""
📝 <b>Cập nhật tín hiệu</b>
📊 {signal['symbol']}
📈 {signal['type']}
💰 Giá mới: ${entry:.2f}
✅ TP mới: ${tp:.2f}
❌ SL mới: ${sl:.2f}
⚖️ R:R = {rr:.1f}
⌚ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
            elif msg_type == "CLOSE":
                pnl = ((signal['close_price'] - entry) / entry) * 100
                if signal['type'] == "SHORT":
                    pnl *= -1
                    
                return f"""
🔒 <b>Đóng tín hiệu</b>
📊 {signal['symbol']}
📈 {signal['type']}
💰 Giá vào: ${entry:.2f}
💵 Giá đóng: ${signal['close_price']:.2f}
📊 P/L: {pnl:+.2f}%
📝 Lý do: {signal.get('close_reason', 'MANUAL')}
⌚ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
            return ""
            
        except Exception as e:
            self.logger.error(f"Error formatting message: {str(e)}")
            return ""

    def _calculate_rsi(self, closes: List[float], period: int = RSI_PERIOD) -> float:
        """Calculate RSI indicator"""
        try:
            if len(closes) < period + 1:
                return 50
                
            deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            
            for i in range(period, len(deltas)):
                avg_gain = (avg_gain * 13 + gains[i]) / 14
                avg_loss = (avg_loss * 13 + losses[i]) / 14
            
            if avg_loss == 0:
                return 100
                
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return round(rsi, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {str(e)}")
            return 50

    def _calculate_ema(self, data: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        try:
            if len(data) < period:
                return data[-1]
                
            multiplier = 2 / (period + 1)
            ema = sum(data[:period]) / period
            
            for price in data[period:]:
                ema = (price - ema) * multiplier + ema
                
            return ema
            
        except Exception as e:
            self.logger.error(f"Error calculating EMA: {str(e)}")
            return data[-1]

    def _calculate_atr(self, klines: List[Dict], period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            if len(klines) < period + 1:
                return 0
                
            true_ranges = []
            for i in range(1, len(klines)):
                high = klines[i]['high']
                low = klines[i]['low']
                prev_close = klines[i-1]['close']
                
                tr1 = high - low
                tr2 = abs(high - prev_close)
                tr3 = abs(low - prev_close)
                
                true_ranges.append(max(tr1, tr2, tr3))
                
            atr = sum(true_ranges[-period:]) / period
            return round(atr, 8)
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {str(e)}")
            return 0
