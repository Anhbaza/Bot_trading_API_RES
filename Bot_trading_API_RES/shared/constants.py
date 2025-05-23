# Bot Names and Versions
TRADING_BOT_NAME = "TradingBot"
ORDER_BOT_NAME = "OrderManagerBot"
VERSION = "1.0.0"

# Message Types
MSG_TYPE_SIGNAL = "SIGNAL"
MSG_TYPE_ORDER_CONFIRM = "ORDER_CONFIRM" 
MSG_TYPE_ORDER_UPDATE = "ORDER_UPDATE"
MSG_TYPE_ORDER_CLOSE = "ORDER_CLOSE"

# Trading Parameters
MAX_TRADES = 5
MAX_TRADES_PER_SYMBOL = 5  # Thêm dòng này
TRADE_SIZE_USDT = 100  # Fixed size $100 per trade
MIN_VOLUME_USDT = 1000000  # 1M USDT
UPDATE_INTERVAL = 300  # 5 minutes

# Risk Management
RISK_PERCENT = 1.0
DEFAULT_LEVERAGE = 5

# Technical Analysis
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
VOLUME_RATIO_MIN = 1.15
MIN_RR_RATIO = 2.0  # Minimum Risk:Reward ratio
MIN_WIN_RATE = 60.0  # Minimum win rate percentage

# Order States
ORDER_STATE_PENDING = "PENDING"
ORDER_STATE_OPEN = "OPEN"
ORDER_STATE_CLOSED = "CLOSED"
ORDER_STATE_CANCELED = "CANCELED"

# Close Reasons
CLOSE_REASON_TP = "TP"
CLOSE_REASON_SL = "SL"
CLOSE_REASON_SIGNAL = "SIGNAL"
CLOSE_REASON_MANUAL = "MANUAL"

# Signal Sources
SIGNAL_SOURCE_RSI = "RSI"
SIGNAL_SOURCE_VOLUME = "VOLUME"
SIGNAL_SOURCE_PRICE_ACTION = "PRICE_ACTION"

# Timeframes
TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']

# Colors for UI
COLOR_PAIRS = {
    'GREEN': 1,
    'CYAN': 2,
    'YELLOW': 3,
    'RED': 4,
    'WHITE': 5,
    'BLUE': 6,
    'MAGENTA': 7,
}

# UI Elements
UI_SYMBOLS = {
    'BORDER_H': '─',
    'BORDER_V': '│',
    'BORDER_TL': '╭',
    'BORDER_TR': '╮',
    'BORDER_BL': '╰',
    'BORDER_BR': '╯',
    'ARROW_UP': '↑',
    'ARROW_DOWN': '↓',
    'CHECK': '✓',
    'CROSS': '✗',
    'WARNING': '⚠',
    'INFO': 'ℹ',
}

# Telegram Message Templates
TELEGRAM_TEMPLATES = {
    'SIGNAL': """
🔔 <b>Tín hiệu giao dịch mới</b>
📊 {symbol}
📈 {type}
💰 Giá vào: ${entry:.2f}
✅ Take Profit: ${tp:.2f}
❌ Stop Loss: ${sl:.2f}
⚖️ R:R = {rr:.1f}
⌚ {time}
""",
    'ORDER_OPEN': """
✅ <b>Đã vào lệnh</b>
📊 {symbol}
📈 {type}
💰 Giá vào: ${entry:.2f}
🎯 TP: ${tp:.2f}
🛑 SL: ${sl:.2f}
💵 Size: ${size:.2f}
⌚ {time}
""",
    'ORDER_CLOSE': """
🔒 <b>Đã đóng lệnh</b>
📊 {symbol}
💰 P/L: ${pnl:+,.2f} ({pnl_percent:+.2f}%)
⏱️ Thời gian: {duration}
📝 Lý do: {reason}
⌚ {time}
""",
    'DAILY_SUMMARY': """
📊 <b>Thống kê ngày {date}</b>
📈 Tổng lệnh: {total_trades}
✅ Thắng: {win_rate:.1f}%
💰 Lợi nhuận: ${profit:+,.2f}
📉 Thua lỗ: ${loss:+,.2f}
🏆 P/L ròng: ${net_pnl:+,.2f}
""",
}

# Database Settings
DB_FILE = "trading_history.db"
DB_BACKUP_DIR = "backups"
MAX_BACKUP_FILES = 7  # Keep last 7 days of backups