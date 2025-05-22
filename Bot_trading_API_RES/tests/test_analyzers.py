"""
Test cases for market analyzers
Tests both MarketTrendAnalyzer and FuturesAnalyzer
"""

import unittest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List

from ..core.analyzer import MarketTrendAnalyzer, FuturesAnalyzer
from ..core.models import MarketState, MarketTrend, SignalData
from ..services import BinanceClient

class TestMarketTrendAnalyzer(unittest.TestCase):
    """Test cases for MarketTrendAnalyzer"""
    
    def setUp(self):
        """Setup test environment"""
        self.api_key = "test_key"
        self.api_secret = "test_secret"
        self.symbol = "BTCUSDT"
        
        self.analyzer = MarketTrendAnalyzer(
            api_key=self.api_key,
            api_secret=self.api_secret,
            symbol=self.symbol
        )
        
        # Mock client
        self.analyzer.client = Mock()
        
        # Setup test data
        self.test_klines = [
            [1621555200000, "50000", "51000", "49000", "50500", "100", 1621555499999, "5000000", 1000, "60", "3000000", "0"],
            [1621555500000, "50500", "52000", "50000", "51500", "150", 1621555799999, "7500000", 1500, "90", "4500000", "0"]
        ]
        
        self.test_orderbook = {
            'lastUpdateId': 1234567,
            'bids': [
                ["50000", "1.000", []],
                ["49900", "2.000", []]
            ],
            'asks': [
                ["50100", "1.500", []],
                ["50200", "2.500", []]
            ]
        }

    def test_calculate_delta(self):
        """Test delta calculation"""
        delta = self.analyzer.calculate_delta_from_klines(self.test_klines)
        self.assertIsInstance(delta, float)
        self.assertTrue(-100 <= delta <= 100)

    def test_get_order_book_state(self):
        """Test order book state analysis"""
        # Mock responses
        self.analyzer.client.get_symbol_ticker.return_value = {'price': '50000'}
        self.analyzer.client.get_order_book.return_value = self.test_orderbook
        self.analyzer.client.get_klines.return_value = self.test_klines
        
        state = self.analyzer.get_order_book_state()
        
        self.assertIsInstance(state, MarketState)
        self.assertTrue(state.vol_ratio > 0)
        self.assertTrue(state.cnt_ratio > 0)

    def test_analyze_trend(self):
        """Test trend analysis"""
        # Mock responses
        self.analyzer.client.get_symbol_ticker.return_value = {'price': '50000'}
        self.analyzer.client.get_order_book.return_value = self.test_orderbook
        self.analyzer.client.get_klines.return_value = self.test_klines
        
        trend = self.analyzer.analyze_trend()
        
        self.assertIsInstance(trend, MarketTrend)
        self.assertIn(trend.type, ['ACCUMULATION', 'DISTRIBUTION', 'NEUTRAL'])
        self.assertTrue(0 <= trend.confidence <= 1)

class TestFuturesAnalyzer(unittest.IsolatedAsyncioTestCase):
    """Test cases for FuturesAnalyzer"""
    
    async def asyncSetUp(self):
        """Setup async test environment"""
        self.client = Mock(spec=BinanceClient)
        self.analyzer = FuturesAnalyzer(
            client=self.client,
            user_login="Anhbaza"
        )
        
        # Setup test data
        self.test_symbol = "BTCUSDT"
        self.test_klines = [
            [1621555200000, "50000", "51000", "49000", "50500", "100", 1621555499999, "5000000", 1000, "60", "3000000", "0"],
            [1621555500000, "50500", "52000", "50000", "51500", "150", 1621555799999, "7500000", 1500, "90", "4500000", "0"]
        ]
        
        self.test_orderbook = {
            'bids': [["50000", "1.000"], ["49900", "2.000"]],
            'asks': [["50100", "1.500"], ["50200", "2.500"]]
        }

    async def test_quick_pre_filter(self):
        """Test quick pre-filter"""
        # Mock responses
        self.client.futures_ticker = AsyncMock(return_value={
            'symbol': self.test_symbol,
            'volume': '1000',
            'lastPrice': '50000'
        })
        
        result = await self.analyzer.quick_pre_filter(self.test_symbol)
        self.assertIsInstance(result, bool)

    async def test_analyze_entry_conditions(self):
        """Test entry condition analysis"""
        # Mock responses
        self.client.futures_klines = AsyncMock(return_value=self.test_klines)
        self.client.futures_order_book = AsyncMock(return_value=self.test_orderbook)
        
        signal = await self.analyzer.analyze_entry_conditions(self.test_symbol)
        
        if signal:
            self.assertIsInstance(signal, SignalData)
            self.assertIn(signal.signal_type, ['LONG', 'SHORT'])
            self.assertTrue(signal.entry > 0)
            self.assertTrue(signal.stop_loss > 0)
            self.assertTrue(signal.take_profit > 0)

    async def test_error_handling(self):
        """Test error handling"""
        # Mock client to raise exception
        self.client.futures_klines = AsyncMock(side_effect=Exception("Test error"))
        
        signal = await self.analyzer.analyze_entry_conditions(self.test_symbol)
        self.assertIsNone(signal)

class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for analyzers"""
    
    async def asyncSetUp(self):
        """Setup integration test environment"""
        # Use real clients but with test credentials
        self.client = BinanceClient(
            api_key="test_key",
            api_secret="test_secret"
        )
        
        self.futures_analyzer = FuturesAnalyzer(
            client=self.client,
            user_login="Anhbaza"
        )
        
        self.trend_analyzer = MarketTrendAnalyzer(
            api_key="test_key",
            api_secret="test_secret",
            symbol="BTCUSDT"
        )

    @unittest.skip("Skip real API calls in CI/CD")
    async def test_full_analysis_flow(self):
        """Test complete analysis flow"""
        symbol = "BTCUSDT"
        
        # Pre-filter
        is_valid = await self.futures_analyzer.quick_pre_filter(symbol)
        if not is_valid:
            self.skipTest("Symbol did not pass pre-filter")
        
        # Analyze entry conditions
        signal = await self.futures_analyzer.analyze_entry_conditions(symbol)
        
        if signal:
            self.assertIsInstance(signal, SignalData)
            self.assertTrue(signal.entry > 0)
            self.assertTrue(signal.stop_loss > 0)
            self.assertTrue(signal.take_profit > 0)
            self.assertGreater(signal.confidence, 0)

def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)

if __name__ == '__main__':
    run_tests()