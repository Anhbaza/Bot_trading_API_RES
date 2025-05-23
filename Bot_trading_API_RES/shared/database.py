import sqlite3
from datetime import datetime
from typing import List, Dict, Any

class Database:
    def __init__(self, db_file: str = "trading_history.db"):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Orders table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            type TEXT NOT NULL,
            entry_price REAL NOT NULL,
            current_price REAL,
            take_profit REAL NOT NULL,
            stop_loss REAL NOT NULL,
            size REAL NOT NULL,
            pnl REAL DEFAULT 0,
            status TEXT NOT NULL,
            entry_time TIMESTAMP,
            close_time TIMESTAMP,
            close_reason TEXT
        )
        """)
        
        # Daily stats table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date DATE PRIMARY KEY,
            trades_count INTEGER DEFAULT 0,
            wins_count INTEGER DEFAULT 0,
            profit_sum REAL DEFAULT 0,
            loss_sum REAL DEFAULT 0
        )
        """)
        
        self.conn.commit()

    def add_order(self, order: Dict[str, Any]) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO orders (
            symbol, type, entry_price, take_profit, stop_loss, 
            size, status, entry_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order['symbol'], order['type'], order['entry_price'],
            order['take_profit'], order['stop_loss'], order['size'],
            'OPEN', datetime.utcnow()
        ))
        self.conn.commit()
        return cursor.lastrowid

    def update_order(self, order_id: int, data: Dict[str, Any]):
        cursor = self.conn.cursor()
        fields = [f"{k} = ?" for k in data.keys()]
        query = f"UPDATE orders SET {', '.join(fields)} WHERE id = ?"
        values = list(data.values()) + [order_id]
        cursor.execute(query, values)
        self.conn.commit()

    def get_active_orders(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE status = 'OPEN'")
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def update_daily_stats(self, pnl: float):
        today = datetime.utcnow().date()
        cursor = self.conn.cursor()
        
        # Get or create today's record
        cursor.execute("INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (today,))
        
        # Update stats
        if pnl > 0:
            cursor.execute("""
            UPDATE daily_stats SET 
                trades_count = trades_count + 1,
                wins_count = wins_count + 1,
                profit_sum = profit_sum + ?
            WHERE date = ?
            """, (pnl, today))
        else:
            cursor.execute("""
            UPDATE daily_stats SET 
                trades_count = trades_count + 1,
                loss_sum = loss_sum + ?
            WHERE date = ?
            """, (abs(pnl), today))
            
        self.conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT 
            SUM(trades_count) as total_trades,
            SUM(wins_count) as total_wins,
            SUM(profit_sum) as total_profit,
            SUM(loss_sum) as total_loss
        FROM daily_stats
        """)
        row = cursor.fetchone()
        
        if row:
            total_trades = row[0] or 0
            total_wins = row[1] or 0
            total_profit = row[2] or 0
            total_loss = row[3] or 0
            
            return {
                'total_trades': total_trades,
                'win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0,
                'total_pnl': total_profit - total_loss,
                'profit_factor': total_profit / total_loss if total_loss > 0 else float('inf')
            }
        return {
            'total_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'profit_factor': 0
        }

    def close(self):
        self.conn.close()
