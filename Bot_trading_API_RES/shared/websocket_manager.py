#!/usr/bin/env python3
"""
WebSocket Manager for Bot Communication
Author: Anhbaza01
Version: 1.0.0
Last Updated: 2025-05-23 20:33:24 UTC

This module manages WebSocket connections between bots, providing:
- Automatic reconnection with exponential backoff
- Heartbeat monitoring
- Message type handling
- Connection status monitoring
"""

import json
import logging
import asyncio
import websockets
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
from enum import Enum

class MessageType(Enum):
    """Message types for bot communication"""
    IDENTIFY = "IDENTIFY"           # Bot identification
    NEW_SIGNAL = "NEW_SIGNAL"       # New trading signal
    UPDATE_SIGNAL = "UPDATE_SIGNAL" # Signal update (TP/SL)
    CLOSE_SIGNAL = "CLOSE_SIGNAL"   # Signal closed
    WATCH_PAIRS = "WATCH_PAIRS"     # Update watched pairs
    SCAN_ALL = "SCAN_ALL"          # Reset to scanning all pairs
    ERROR = "ERROR"                # Error message
    HEARTBEAT = "HEARTBEAT"        # Connection check

class WebSocketManager:
    def __init__(
        self, 
        name: str,
        host: str = "localhost",
        port: int = 8765,
        logger: Optional[logging.Logger] = None,
        reconnect_interval: int = 5,
        heartbeat_interval: int = 30
    ):
        """
        Initialize WebSocket Manager
        
        Args:
            name (str): Bot name for identification
            host (str): WebSocket server host
            port (int): WebSocket server port
            logger (Logger): Optional logger instance
            reconnect_interval (int): Seconds between reconnection attempts
            heartbeat_interval (int): Seconds between heartbeats
        """
        self.name = name
        self.host = host
        self.port = port
        self.logger = logger or logging.getLogger(__name__)
        self.websocket = None
        self.handlers = {}
        self._is_running = False
        self.reconnect_interval = reconnect_interval
        self.heartbeat_interval = heartbeat_interval
        self.last_heartbeat = datetime.utcnow()
        self.connection_task = None
        self.heartbeat_task = None
        self.user = "Anhbaza01"
        self.version = "1.0.0"
        
        # Setup default handlers
        self.register_handler(MessageType.HEARTBEAT.value, self._handle_heartbeat)
        self.register_handler(MessageType.ERROR.value, self._handle_error)

    async def connect(self) -> bool:
        """
        Connect to WebSocket server
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            uri = f"ws://{self.host}:{self.port}"
            self.logger.info(f"[*] Connecting to {uri}...")
            
            # Use asyncio.wait_for for connection timeout
            try:
                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        uri,
                        ping_interval=20,  # Send ping every 20 seconds
                        ping_timeout=10,   # Wait 10 seconds for pong
                        close_timeout=5    # Wait 5 seconds for close handshake
                    ),
                    timeout=10  # 10 seconds connection timeout
                )
            except asyncio.TimeoutError:
                self.logger.error(f"[-] Connection timeout to {uri}")
                return False
            
            # Send identification immediately after connection
            identify_msg = {
                "type": MessageType.IDENTIFY.value,
                "data": {
                    "name": self.name,
                    "user": self.user,
                    "version": self.version,
                    "time": datetime.utcnow().isoformat()
                }
            }
            
            await self.websocket.send(json.dumps(identify_msg))
            self.logger.info(f"[+] Connected and identified as {self.name}")
            
            # Start heartbeat
            self.last_heartbeat = datetime.utcnow()
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            return True
            
        except ConnectionRefusedError:
            self.logger.error(f"[-] Connection refused to {uri}. Is the server running?")
            return False
        except Exception as e:
            self.logger.error(f"[-] Connection error: {str(e)}")
            return False

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send message through WebSocket
        
        Args:
            message (dict): Message to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            if not self.is_connected():
                raise ConnectionError("WebSocket not connected")
                
            # Add metadata to message
            if isinstance(message, dict):
                message.update({
                    "timestamp": datetime.utcnow().isoformat(),
                    "sender": self.name,
                    "user": self.user,
                    "version": self.version
                })
            
            await self.websocket.send(json.dumps(message))
            
            # Log message type and timestamp
            msg_type = message.get("type", "UNKNOWN")
            self.logger.debug(f"[>] Sent {msg_type} message")
            
            return True
            
        except websockets.exceptions.ConnectionClosed:
            self.logger.error("[-] Connection closed while sending message")
            return False
        except Exception as e:
            self.logger.error(f"[-] Error sending message: {str(e)}")
            return False

    def register_handler(self, message_type: str, handler: Callable):
        """
        Register message handler
        
        Args:
            message_type (str): Type of message to handle
            handler (callable): Function to handle message
        """
        self.handlers[message_type] = handler
        self.logger.info(f"[+] Registered handler for {message_type}")

    async def _handle_heartbeat(self, data: Dict[str, Any]):
        """Handle heartbeat message"""
        self.last_heartbeat = datetime.utcnow()
        await self.send_message({
            "type": MessageType.HEARTBEAT.value,
            "data": {"status": "alive"}
        })

    async def _handle_error(self, data: Dict[str, Any]):
        """Handle error message"""
        error_msg = data.get("message", "Unknown error")
        self.logger.error(f"[ERROR] Received from peer: {error_msg}")

    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self._is_running and self.is_connected():
            try:
                await self.send_message({
                    "type": MessageType.HEARTBEAT.value,
                    "data": {"status": "alive"}
                })
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                self.logger.error(f"[-] Heartbeat error: {str(e)}")
                break

    async def listen(self):
        """Listen for incoming messages"""
        self._is_running = True
        
        # Start connection checker
        if self.connection_task:
            self.connection_task.cancel()
        self.connection_task = asyncio.create_task(self._check_connection())
        
        while self._is_running:
            try:
                if not self.is_connected():
                    await asyncio.sleep(self.reconnect_interval)
                    continue
                    
                # Receive and parse message
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Log received message
                msg_type = data.get("type", "UNKNOWN")
                msg_time = data.get("timestamp", "Unknown time")
                self.logger.info(f"[<] Received {msg_type} message at {msg_time}")
                
                if msg_type in self.handlers:
                    await self.handlers[msg_type](data.get("data", {}))
                else:
                    self.logger.warning(f"[!] No handler for message type: {msg_type}")
                    
            except websockets.exceptions.ConnectionClosed:
                self.logger.error("[-] WebSocket connection closed")
                await self.reconnect()
            except json.JSONDecodeError:
                self.logger.error("[-] Invalid JSON message received")
            except Exception as e:
                self.logger.error(f"[-] Error processing message: {str(e)}")
                await asyncio.sleep(1)

    def is_connected(self) -> bool:
        """
        Check if WebSocket is connected
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            return (self.websocket is not None and 
                   self.websocket.open and
                   not self.websocket.closed)
        except Exception:
            return False

    async def reconnect(self):
        """
        Attempt to reconnect with exponential backoff
        
        Returns:
            bool: True if reconnected successfully, False otherwise
        """
        retry_count = 0
        max_retries = 5
        base_delay = 1  # Start with 1 second
        
        while self._is_running and retry_count < max_retries:
            try:
                retry_count += 1
                delay = base_delay * (2 ** (retry_count - 1))  # Exponential backoff
                
                self.logger.info(
                    f"[*] Reconnection attempt {retry_count}/{max_retries} "
                    f"(waiting {delay}s)..."
                )
                
                await asyncio.sleep(delay)
                
                if await self.connect():
                    self.logger.info("[+] Reconnected successfully")
                    return True
                    
            except Exception as e:
                self.logger.error(f"[-] Reconnection attempt failed: {str(e)}")
        
        self.logger.error(
            f"[-] Failed to reconnect after {max_retries} attempts. "
            "Check if WebSocket server is running."
        )
        return False

    async def _check_connection(self):
        """Check connection health and reconnect if needed"""
        while self._is_running:
            try:
                if not self.is_connected():
                    self.logger.warning("[!] Connection lost, attempting to reconnect...")
                    if await self.reconnect():
                        continue
                    else:
                        await asyncio.sleep(30)  # Wait longer before next attempt
                        continue
                
                # Calculate time since last heartbeat
                heartbeat_age = (datetime.utcnow() - self.last_heartbeat).total_seconds()
                
                # If no heartbeat received for too long, reconnect
                if heartbeat_age > self.heartbeat_interval * 2:
                    self.logger.warning(
                        f"[!] No heartbeat for {heartbeat_age:.1f}s, reconnecting..."
                    )
                    await self.reconnect()
                    continue
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"[-] Connection check error: {str(e)}")
                await asyncio.sleep(5)

    async def stop(self):
        """Stop WebSocket manager"""
        try:
            self._is_running = False
            
            # Cancel background tasks
            if self.connection_task:
                self.connection_task.cancel()
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            
            if self.websocket:
                self.logger.info("[*] Closing WebSocket connection...")
                await self.websocket.close()
                self.logger.info("[+] WebSocket connection closed")
                
        except Exception as e:
            self.logger.error(f"[-] Error stopping WebSocket manager: {str(e)}")
        finally:
            self.websocket = None

    async def send_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        Send trading signal
        
        Args:
            signal_data (dict): Trading signal data
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        return await self.send_message({
            "type": MessageType.NEW_SIGNAL.value,
            "data": signal_data
        })

    async def send_signal_update(self, signal_data: Dict[str, Any]) -> bool:
        """
        Send signal update
        
        Args:
            signal_data (dict): Updated signal data
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        return await self.send_message({
            "type": MessageType.UPDATE_SIGNAL.value,
            "data": signal_data
        })

    async def send_signal_close(self, signal_data: Dict[str, Any]) -> bool:
        """
        Send signal close notification
        
        Args:
            signal_data (dict): Signal closing data
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        return await self.send_message({
            "type": MessageType.CLOSE_SIGNAL.value,
            "data": signal_data
        })

    async def update_watched_pairs(self, pairs: List[str]) -> bool:
        """
        Update list of watched pairs
        
        Args:
            pairs (list): List of pair symbols to watch
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        return await self.send_message({
            "type": MessageType.WATCH_PAIRS.value,
            "data": {"pairs": pairs}
        })

    async def reset_to_scan_all(self) -> bool:
        """
        Reset to scanning all pairs
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        return await self.send_message({
            "type": MessageType.SCAN_ALL.value,
            "data": {}
        })