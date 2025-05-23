"""
Telegram handler for order management bot
Author: Anhbaza01
Last Updated: 2025-05-23 11:08:59
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional, Callable
from shared.constants import (
    MSG_TYPE_SIGNAL, MSG_TYPE_ORDER_CONFIRM,
    MSG_TYPE_ORDER_UPDATE, MSG_TYPE_ORDER_CLOSE,
    ORDER_BOT_NAME
)
from shared.telegram_service import TelegramService
from order_management.services.order_manager import OrderManager

class TelegramHandler:
    def __init__(
        self,
        token: str,
        chat_id: str,
        order_manager: OrderManager,
        on_signal_received: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_order_update: Optional[Callable[[str, Decimal], None]] = None
    ):
        """
        Initialize Telegram handler
        
        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID
            order_manager: Order manager instance
            on_signal_received: Callback when new signal is received
            on_order_update: Callback when order update is received
        """
        self.logger = logging.getLogger("TelegramHandler")
        self.telegram = TelegramService(token, chat_id, ORDER_BOT_NAME)
        self.order_manager = order_manager
        self.on_signal_received = on_signal_received
        self.on_order_update = on_order_update

    aasync def handle_message(self, message: str) -> None:
     """Handle incoming Telegram message"""
     try:
        print(f"\n[DEBUG] TelegramHandler received message: {message}")
        
        # Try to parse as command first
        if message.startswith("CMD:"):
            try:
                json_str = message[4:].strip()
                print(f"\n[DEBUG] Parsing command JSON: {json_str}")
                
                command = json.loads(json_str)
                if command.get("type") == "SIGNAL":
                    signal_data = command.get("data", {})
                    print(f"\n[DEBUG] Found signal data: {signal_data}")
                    
                    # Format signal for GUI
                    formatted_signal = {
                        "symbol": signal_data["symbol"],
                        "signal_type": signal_data["signal_type"],
                        "entry": float(signal_data["entry"]),
                        "take_profit": float(signal_data["take_profit"]),
                        "stop_loss": float(signal_data["stop_loss"]),
                        "confidence": float(signal_data.get("confidence", 0.55)),
                        "timestamp": datetime.utcnow().strftime('%H:%M:%S')
                    }
                    
                    print(f"\n[DEBUG] Formatted signal: {formatted_signal}")
                    
                    # Send to GUI
                    if self.on_signal_received:
                        print("\n[DEBUG] Sending signal to GUI...")
                        self.on_signal_received(formatted_signal)
                        print("\n[DEBUG] Signal sent to GUI")
                    else:
                        print("\n[DEBUG] No signal callback registered!")
                        
            except json.JSONDecodeError as e:
                print(f"\n[DEBUG] JSON parse error: {str(e)}")
                print(f"\n[DEBUG] Raw message was: {message}")
        
        # Also check for regular messages containing signal data
        else:
            print(f"\n[DEBUG] Regular message received: {message}")
            # Rest of your regular message handling code...
            
     except Exception as e:
        print(f"\n[DEBUG] Error in handle_message: {str(e)}")
        print(f"\n[DEBUG] Message was: {message}")

    async def _process_command(self, command: Dict[str, Any]) -> None:
        """
        Process parsed command
        
        Args:
            command: Parsed command data
        """
        cmd_type = command.get('type')
        data = command.get('data', {})

        try:
            if cmd_type == MSG_TYPE_SIGNAL:
                await self._handle_signal(data)
            elif cmd_type == MSG_TYPE_ORDER_UPDATE:
                await self._handle_order_update(data)
            else:
                self.logger.warning(f"Unknown command type: {cmd_type}")

        except Exception as e:
            self.logger.error(f"Error processing command {cmd_type}: {str(e)}")

    async def _handle_signal(self, data: Dict[str, Any]) -> None:
        """Handle new trading signal"""
        try:
            # Log received signal
            self.logger.info(f"Processing signal: {data}")
            
            # Validate required fields
            required_fields = ['symbol', 'signal_type', 'entry', 'take_profit', 'stop_loss']
            if not all(field in data for field in required_fields):
                self.logger.error(f"Invalid signal data - missing fields: {data}")
                return

            # Format signal data
            signal = {
                'symbol': data['symbol'],
                'signal_type': data['signal_type'],
                'entry': float(data['entry']),
                'take_profit': float(data['take_profit']),
                'stop_loss': float(data['stop_loss']),
                'timestamp': datetime.utcnow().strftime('%H:%M:%S'),
                'confidence': data.get('confidence', 0.55)
            }

            # Notify GUI via callback
            if self.on_signal_received:
                self.logger.info(f"Sending signal to GUI: {signal}")
                self.on_signal_received(signal)
            else:
                self.logger.warning("No signal callback registered")

        except Exception as e:
            self.logger.error(f"Error handling signal: {str(e)}")
    async def _handle_order_update(self, data: Dict[str, Any]) -> None:
        """
        Handle order update
        
        Args:
            data: Order update data
        """
        try:
            symbol = data.get('symbol')
            price = data.get('price')

            if not symbol or price is None:
                self.logger.error("Invalid order update: missing symbol or price")
                return

            # Convert price to Decimal
            current_price = Decimal(str(price))

            # Update order
            order, close_reason = self.order_manager.update_order(symbol, current_price)

            # If order was closed, notify trading bot
            if close_reason:
                await self.telegram.send_command(
                    MSG_TYPE_ORDER_CLOSE,
                    {
                        "symbol": symbol,
                        "reason": close_reason,
                        "pnl": float(order.pnl),
                        "duration": order.duration
                    }
                )

            # Notify callback if registered
            if self.on_order_update:
                self.on_order_update(symbol, current_price)

        except Exception as e:
            self.logger.error(f"Error handling order update: {str(e)}")

    async def send_order_confirmation(self, symbols: list[str]) -> None:
        """
        Send order confirmation to trading bot
        
        Args:
            symbols: List of confirmed symbol
        """
        try:
            await self.telegram.send_command(
                MSG_TYPE_ORDER_CONFIRM,
                {"symbols": symbols}
            )
            self.logger.info(f"Sent confirmation for symbols: {symbols}")

        except Exception as e:
            self.logger.error(f"Error sending order confirmation: {str(e)}")

    async def send_error(self, error: str) -> None:
        """
        Send error message
        
        Args:
            error: Error message
        """
        await self.telegram.send_error(error)

    async def send_warning(self, warning: str) -> None:
        """
        Send warning message
        
        Args:
            warning: Warning message
        """
        await self.telegram.send_warning(warning)

    async def send_success(self, message: str) -> None:
        """
        Send success message
        
        Args:
            message: Success message
        """
        await self.telegram.send_success(message)

    def format_signal_message(self, signal: Dict[str, Any]) -> str:
        """
        Format signal message for display
        
        Args:
            signal: Signal data
            
        Returns:
            Formatted message text
        """
        return (
            f"🔔 <b>Tín hiệu Mới - {signal['symbol']}</b>\n\n"
            f"Loại: {'📈' if signal['signal_type'] == 'LONG' else '📉'} {signal['signal_type']}\n"
            f"Giá vào: ${signal['entry']:.4f}\n"
            f"Take Profit: ${signal['take_profit']:.4f}\n"
            f"Stop Loss: ${signal['stop_loss']:.4f}\n"
            f"Thời gian: {signal['timestamp']}\n\n"
            f"Lý do:\n{signal.get('reason', 'Không có')}"
        )

    def format_order_message(self, order: Dict[str, Any]) -> str:
        """
        Format order message for display
        
        Args:
            order: Order data
            
        Returns:
            Formatted message text
        """
        return (
            f"📊 <b>Trạng thái Lệnh - {order['symbol']}</b>\n\n"
            f"Loại: {'📈' if order['type'] == 'LONG' else '📉'} {order['type']}\n"
            f"Giá vào: {order['entry']}\n"
            f"Giá hiện tại: {order['current']}\n"
            f"P/L: {order['pnl']} ({order['pnl_percent']})\n"
            f"Thời gian: {order['duration']}\n"
            f"Trạng thái: {order['status']}"
        )
