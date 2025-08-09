"""
Connect to VPS to read signals from the actual running system
The real crypto-paper-trading is on the VPS, not local!
"""

import paramiko
import sqlite3
import json
import os
from datetime import datetime
import tempfile
import requests

class VPSSignalReader:
    """Read signals from the VPS where the system is actually running"""
    
    def __init__(self):
        # VPS connection details
        self.vps_host = '172.93.51.42'
        self.vps_user = 'root'
        self.vps_key_path = os.path.expanduser('~/.ssh/tao_alpha_dca_key')
        
        # Remote paths on VPS
        self.remote_project_path = '/root/crypto-paper-trading'
        self.remote_db_path = '/root/crypto-paper-trading/trade_log.db'
        
        # Telegram settings (these work locally)
        self.telegram_token = '8405614465:AAGl1MFkI4T7dksrk93oHXJOilcBXH36Do0'
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '6585156851')
        
    def connect_ssh(self):
        """Connect to VPS via SSH"""
        print(f"Connecting to VPS at {self.vps_host}...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Try with key file
            if os.path.exists(self.vps_key_path):
                ssh.connect(
                    hostname=self.vps_host,
                    username=self.vps_user,
                    key_filename=self.vps_key_path
                )
                print("Connected to VPS successfully!")
            else:
                print(f"SSH key not found at {self.vps_key_path}")
                print("Please ensure your SSH key is available")
                return None
                
            return ssh
            
        except Exception as e:
            print(f"Failed to connect to VPS: {e}")
            return None
    
    def get_latest_signals(self, ssh):
        """Get latest signals from VPS database"""
        print("\nFetching signals from VPS database...")
        
        # Command to run on VPS
        command = f"""
cd {self.remote_project_path} && python3 -c "
import sqlite3
import json

conn = sqlite3.connect('trade_log.db')
cursor = conn.cursor()

# Get last 5 unprocessed signals
cursor.execute('''
    SELECT id, timestamp, symbol, side, entry_price, stop_loss, take_profit
    FROM signal_log
    WHERE processed = 0
    AND symbol IS NOT NULL
    ORDER BY id DESC
    LIMIT 5
''')

signals = cursor.fetchall()
if signals:
    for sig in signals:
        print(json.dumps({{
            'id': sig[0],
            'timestamp': sig[1],
            'symbol': sig[2],
            'side': sig[3],
            'entry': sig[4],
            'sl': sig[5],
            'tp': sig[6]
        }}))
else:
    print('NO_SIGNALS')
    
conn.close()
"
        """
        
        # Execute command
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        if error:
            print(f"Error on VPS: {error}")
            return []
        
        # Parse signals
        signals = []
        for line in output.strip().split('\n'):
            if line and line != 'NO_SIGNALS':
                try:
                    signal = json.loads(line)
                    signals.append(signal)
                except:
                    pass
        
        if signals:
            print(f"Found {len(signals)} new signals on VPS")
        else:
            print("No new signals found on VPS")
            
        return signals
    
    def check_system_status(self, ssh):
        """Check if the system is running on VPS"""
        print("\nChecking system status on VPS...")
        
        # Check PM2 processes
        stdin, stdout, stderr = ssh.exec_command("pm2 list")
        output = stdout.read().decode()
        
        print("PM2 Processes:")
        print(output)
        
        # Check if signal monitoring is active
        stdin, stdout, stderr = ssh.exec_command(f"cd {self.remote_project_path} && tail -n 20 logs/trading.log")
        logs = stdout.read().decode()
        
        print("\nRecent log entries:")
        for line in logs.split('\n')[-5:]:
            print(f"  {line}")
    
    def send_telegram_alert(self, signal):
        """Send alert for a signal"""
        message = f"""
🚨 VPS SIGNAL DETECTED 🚨

Symbol: {signal['symbol']}
Side: {signal['side']}
Entry: {signal['entry']}
Stop: {signal['sl']}
Target: {signal['tp']}

Signal ID: {signal['id']}
Time: {signal['timestamp']}

[Execute in Breakout Terminal]
        """
        
        url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
        response = requests.post(url, json={
            'chat_id': self.telegram_chat_id,
            'text': message
        })
        
        if response.status_code == 200:
            print(f"Alert sent for signal {signal['id']}")
        else:
            print(f"Failed to send alert: {response.text}")
    
    def run(self):
        """Main execution"""
        print("=" * 50)
        print("VPS SIGNAL READER")
        print("=" * 50)
        
        # Connect to VPS
        ssh = self.connect_ssh()
        if not ssh:
            return
        
        try:
            # Check system status
            self.check_system_status(ssh)
            
            # Get signals
            signals = self.get_latest_signals(ssh)
            
            # Process signals
            if signals:
                print(f"\nProcessing {len(signals)} signals...")
                for signal in signals:
                    print(f"\nSignal: {signal['symbol']} {signal['side']}")
                    
                    # Here you would validate with prop firm rules
                    # For now, just show the signal
                    
                    # Optional: Send alert
                    # self.send_telegram_alert(signal)
            
        finally:
            ssh.close()
            print("\nDisconnected from VPS")

def main():
    """Run the VPS signal reader"""
    reader = VPSSignalReader()
    reader.run()

if __name__ == "__main__":
    main()