#!/usr/bin/env python3
"""Start the complete automated trading system"""

import subprocess
import sys
import os
import time
import signal
from datetime import datetime

def start_service(name, command):
    """Start a service and return the process"""
    print(f"Starting {name}...")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        time.sleep(2)  # Give it time to start
        
        if process.poll() is None:
            print(f"[OK] {name} started (PID: {process.pid})")
            return process
        else:
            print(f"[FAILED] {name} failed to start")
            stdout, stderr = process.communicate()
            print(f"Error: {stderr.decode()}")
            return None
    except Exception as e:
        print(f"[ERROR] Failed to start {name}: {e}")
        return None

def main():
    print("="*60)
    print("CRYPTO PAPER TRADING - AUTOMATED SYSTEM STARTUP")
    print("="*60)
    print(f"Starting at: {datetime.now()}")
    print()
    
    processes = []
    
    # 1. Start the automated signal monitor
    signal_monitor = start_service(
        "Automated Signal Monitor",
        f"{sys.executable} automated_signal_monitor.py"
    )
    if signal_monitor:
        processes.append(signal_monitor)
    
    # 2. Start the position monitor for trailing stops
    position_monitor = start_service(
        "Position Monitor (Trailing TP)",
        f"{sys.executable} position_monitor.py"
    )
    if position_monitor:
        processes.append(position_monitor)
    
    print("\n" + "="*60)
    print("SYSTEM STATUS:")
    print("="*60)
    
    if len(processes) == 2:
        print("[OK] All services started successfully!")
        print("\nServices running:")
        print("1. Automated Signal Monitor - Watching Telegram for new signals")
        print("2. Position Monitor - Managing trailing take profits")
        print("\nMonitoring will continue in the background.")
        print("Check the dashboard at crypto.profithits.app for updates")
        print("\nPress Ctrl+C to stop all services")
        
        try:
            # Keep the script running
            while True:
                time.sleep(60)
                # Check if processes are still running
                for i, proc in enumerate(processes):
                    if proc.poll() is not None:
                        print(f"\n[WARNING] Process {i+1} has stopped!")
        except KeyboardInterrupt:
            print("\n\nShutting down services...")
            for proc in processes:
                proc.terminate()
            print("All services stopped.")
    else:
        print("[ERROR] Some services failed to start")
        print("Check the error messages above")
        
        # Clean up any started processes
        for proc in processes:
            if proc:
                proc.terminate()

if __name__ == "__main__":
    main()