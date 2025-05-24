#!/usr/bin/env python3
"""
Console Manager for Bot UI
Author: Anhbaza01
Version: 1.0.0
Last Updated: 2025-05-23 20:20:15 UTC
"""

import os
import sys
import asyncio
import curses
from datetime import datetime
from typing import List, Dict, Optional

class ConsoleManager:
    def __init__(self, title: str = "Trading Bot"):
        self.title = title
        self.screen = None
        self.last_logs: List[str] = []
        self.max_logs = 10
        self._is_running = True

    def start(self):
        """Start console UI"""
        # Initialize curses
        self.screen = curses.initscr()
        curses.start_color()
        curses.use_default_colors()
        curses.curs_set(0)  # Hide cursor
        
        # Initialize color pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        
        # Enable keypad and disable echo
        self.screen.keypad(1)
        curses.noecho()
        
        # Clear screen
        self.screen.clear()
        self.screen.refresh()

    def stop(self):
        """Stop console UI"""
        if self.screen:
            self.screen.keypad(0)
            curses.echo()
            curses.endwin()
        self._is_running = False

    def add_log(self, message: str):
        """Add message to log history"""
        self.last_logs.append(message)
        if len(self.last_logs) > self.max_logs:
            self.last_logs.pop(0)

    def update(
        self,
        scanning_mode: str,
        total_pairs: int,
        watched_pairs: List[str],
        active_signals: Dict,
        next_scan: datetime,
        ws_connected: bool,
        user: str
    ):
        """Update console display"""
        try:
            if not self.screen or not self._is_running:
                return

            # Clear screen
            self.screen.clear()
            
            # Get screen dimensions
            max_y, max_x = self.screen.getmaxyx()
            current_y = 0

            # Draw title
            title = f"=== {self.title} ==="
            self.screen.addstr(current_y, 0, title, curses.A_BOLD)
            current_y += 1

            # Draw current time and user
            time_str = f"Time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            self.screen.addstr(current_y, 0, time_str)
            current_y += 1
            
            user_str = f"User: {user}"
            self.screen.addstr(current_y, 0, user_str)
            current_y += 1

            # Draw separator
            self.screen.addstr(current_y, 0, "=" * len(title))
            current_y += 2

            # Draw scanning mode
            mode_str = f"Scanning Mode: {scanning_mode}"
            self.screen.addstr(current_y, 0, mode_str, curses.color_pair(4))
            current_y += 1

            pairs_str = f"Monitoring: {total_pairs} pairs"
            self.screen.addstr(current_y, 0, pairs_str)
            current_y += 2

            # Draw watched pairs if any
            if watched_pairs:
                self.screen.addstr(current_y, 0, "Watched Pairs:", curses.A_BOLD)
                current_y += 1
                pairs_text = ", ".join(watched_pairs)
                self.screen.addstr(current_y, 0, pairs_text)
                current_y += 2

            # Draw active signals
            self.screen.addstr(current_y, 0, "Active Signals:", curses.A_BOLD)
            current_y += 1

            if active_signals:
                for signal_id, signal in active_signals.items():
                    signal_color = (curses.color_pair(1) 
                                  if signal['type'] == 'LONG' 
                                  else curses.color_pair(2))
                    
                    self.screen.addstr(current_y, 0, 
                        f"{signal['symbol']} - {signal['type']}", signal_color)
                    current_y += 1
                    
                    self.screen.addstr(current_y, 2, 
                        f"Entry: {signal['entry']:.8f}")
                    current_y += 1
                    
                    self.screen.addstr(current_y, 2,
                        f"TP: {signal['tp']:.8f}")
                    current_y += 1
                    
                    self.screen.addstr(current_y, 2,
                        f"SL: {signal['sl']:.8f}")
                    current_y += 1
                    
                    conf_color = (curses.color_pair(1) 
                                if signal.get('confidence', 0) >= 75 
                                else curses.color_pair(3))
                    self.screen.addstr(current_y, 2,
                        f"Confidence: {signal.get('confidence', 0)}%", conf_color)
                    current_y += 2
            else:
                self.screen.addstr(current_y, 0, "No active signals")
                current_y += 2

            # Draw next scan time
            next_scan_str = f"Next scan at: {next_scan.strftime('%H:%M:%S')} UTC"
            self.screen.addstr(current_y, 0, next_scan_str)
            current_y += 2

            # Draw WebSocket status
            ws_status = "[CONNECTED]" if ws_connected else "[DISCONNECTED]"
            ws_color = curses.color_pair(1) if ws_connected else curses.color_pair(2)
            self.screen.addstr(current_y, 0, f"WebSocket: {ws_status}", ws_color)
            current_y += 2

            # Draw recent logs
            self.screen.addstr(current_y, 0, "Recent Logs:", curses.A_BOLD)
            current_y += 1
            self.screen.addstr(current_y, 0, "-" * 50)
            current_y += 1

            for log in self.last_logs[-8:]:  # Show last 8 logs
                if current_y < max_y - 1:  # Prevent writing outside screen
                    self.screen.addstr(current_y, 0, log)
                    current_y += 1

            # Draw footer
            footer = "Press Ctrl+C to exit"
            if current_y < max_y - 1:
                self.screen.addstr(max_y-1, 0, footer, curses.A_DIM)

            # Refresh screen
            self.screen.refresh()

        except Exception as e:
            # In case of error, try to restore terminal
            self.stop()
            print(f"Console error: {str(e)}")
