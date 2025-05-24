 #!/usr/bin/env python3
"""
WebSocket Server for Bot Communication
Author: Anhbaza01
Version: 1.0.0
Last Updated: 2025-05-23 19:58:23 UTC
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Dict, Set

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s UTC | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('WebSocketServer')

class WebSocketServer:
    def __init__(self, host: str = 'localhost', port: int = 8765):
        """Initialize WebSocket server"""
        self.host = host
        self.port = port
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.trading_bot = None
        self.order_manager = None

    async def register_client(self, websocket: websockets.WebSocketServerProtocol, name: str):
        """Register new client connection"""
        self.clients[name] = websocket
        logger.info(f"[+] Client registered: {name}")
        
        # Identify specific clients
        if name == "TradingBot":
            self.trading_bot = websocket
            logger.info("[+] Trading Bot connected")
        elif name == "OrderManager":
            self.order_manager = websocket
            logger.info("[+] Order Manager connected")

    async def unregister_client(self, name: str):
        """Unregister client connection"""
        if name in self.clients:
            del self.clients[name]
            logger.info(f"[-] Client disconnected: {name}")
            
            # Clear specific client references
            if name == "TradingBot":
                self.trading_bot = None
            elif name == "OrderManager":
                self.order_manager = None

    async def forward_message(self, sender: str, message: Dict):
        """Forward message to appropriate recipient"""
        try:
            # Determine recipient based on message type and sender
            if sender == "TradingBot" and self.order_manager:
                await self.order_manager.send(json.dumps(message))
                logger.info(f"[>] Message forwarded: TradingBot -> OrderManager")
            elif sender == "OrderManager" and self.trading_bot:
                await self.trading_bot.send(json.dumps(message))
                logger.info(f"[>] Message forwarded: OrderManager -> TradingBot")
            else:
                logger.warning(f"[!] Cannot forward message, recipient not connected")
                
        except Exception as e:
            logger.error(f"[-] Error forwarding message: {str(e)}")

    async def handler(self, websocket: websockets.WebSocketServerProtocol):
        """Handle client connection"""
        client_name = None
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    # Handle client identification
                    if data['type'] == 'IDENTIFY':
                        client_name = data['data']['name']
                        await self.register_client(websocket, client_name)
                        continue
                    
                    # Log message
                    logger.info(
                        f"[*] Message received from {client_name}:\n"
                        f"    Type: {data.get('type')}\n"
                        f"    Time: {data.get('timestamp', datetime.utcnow().isoformat())}"
                    )
                    
                    # Forward message
                    await self.forward_message(client_name, data)
                    
                except json.JSONDecodeError:
                    logger.error("[-] Invalid JSON message received")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[-] Connection closed")
        finally:
            if client_name:
                await self.unregister_client(client_name)

    async def start(self):
        """Start WebSocket server"""
        try:
            server = await websockets.serve(self.handler, self.host, self.port)
            logger.info(f"[+] WebSocket server started on ws://{self.host}:{self.port}")
            
            # Keep server running
            await server.wait_closed()
            
        except Exception as e:
            logger.error(f"[-] Server error: {str(e)}")

def main():
    """Main entry point"""
    try:
        # Create server instance
        server = WebSocketServer()
        
        # Set event loop policy for Windows
        if asyncio.get_event_loop().is_closed():
            asyncio.set_event_loop(asyncio.new_event_loop())
            
        # Get event loop
        loop = asyncio.get_event_loop()
        
        # Start server
        print(f"\n[*] Starting WebSocket server...")
        print(f"[*] Press Ctrl+C to stop")
        
        loop.run_until_complete(server.start())
        
    except KeyboardInterrupt:
        print("\n[!] Server stopped by user")
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {str(e)}")
    finally:
        # Close event loop
        loop.close()

if __name__ == "__main__":
    main()
