# Bot Trading API REST

## Overview
Advanced cryptocurrency trading bot for Binance Futures with real-time market analysis and Telegram notifications.

**Author:** Anhbaza  
**Version:** 1.0.0  
**Last Updated:** 2025-05-22 13:50:39 UTC

## Features
- Real-time market analysis
- Volume profile analysis
- Multiple timeframe trend detection
- Automatic signal generation
- Telegram notifications
- Rate limiting and error handling
- Comprehensive logging

## Installation

### Prerequisites
- Python 3.8+
- Binance account with API access
- Telegram bot token

### Setup
1. Clone the repository:
```bash
git clone https://github.com/Anhbaza/Bot_trading_API_RES.git
cd Bot_trading_API_RES
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
- Copy `data.env.example` to `data.env`
- Fill in your API credentials and settings

### Usage
Run the bot:
```bash
python Bot_trading_API_RES.py
```

## Configuration

### Environment Variables
Required variables in `data.env`:
- `BINANCE_API_KEY`: Your Binance API key
- `BINANCE_API_SECRET`: Your Binance API secret
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID

### Trading Parameters
Configurable parameters in `config/settings.py`:
- Timeframes
- Volume thresholds
- Risk management settings
- Rate limiting

## Project Structure
```
Bot_trading_API_RES/
├── config/           # Configuration files
├── core/            # Core trading logic
│   ├── analyzer/    # Market analysis
│   ├── models/      # Data models
│   └── utils/       # Utility functions
├── services/        # External services
└── tests/           # Test suite
```

## Testing
Run the test suite:
```bash
python -m unittest discover tests
```

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
MIT License - see LICENSE file for details

## Disclaimer
This bot is for educational purposes only. Use at your own risk. The author is not responsible for any financial losses incurred while using this bot. 
