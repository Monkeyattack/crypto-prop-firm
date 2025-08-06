#!/bin/bash
# Set up systemd service for crypto trading app

set -e

echo "=== Setting up Systemd Service ==="

# Copy service file
echo "Installing systemd service..."
sudo cp /root/crypto-paper-trading/crypto-trading.service /etc/systemd/system/

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable the service
echo "Enabling crypto-trading service..."
sudo systemctl enable crypto-trading

# Start the service
echo "Starting crypto-trading service..."
sudo systemctl start crypto-trading

# Check status
echo "Service status:"
sudo systemctl status crypto-trading --no-pager

# Show logs
echo "Recent logs:"
sudo journalctl -u crypto-trading --no-pager -n 20

echo "Systemd service setup complete!"
echo "Commands:"
echo "  sudo systemctl status crypto-trading    # Check status"
echo "  sudo systemctl restart crypto-trading   # Restart service"
echo "  sudo journalctl -u crypto-trading -f    # View live logs"