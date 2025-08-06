#!/bin/bash
# Set up nginx configuration for crypto.profithits.app

set -e

echo "=== Setting up Nginx for crypto.profithits.app ==="

# Copy nginx configuration
echo "Installing nginx configuration..."
sudo cp /root/crypto-paper-trading/nginx_crypto.conf /etc/nginx/sites-available/crypto.profithits.app

# Create simplified configuration to avoid escaping issues
sudo tee /etc/nginx/sites-available/crypto.profithits.app << 'EOF'
server {
    listen 80;
    server_name crypto.profithits.app;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_buffering off;
        proxy_read_timeout 86400;
    }

    access_log /var/log/nginx/crypto.profithits.app.access.log;
    error_log /var/log/nginx/crypto.profithits.app.error.log;
}
EOF

# Enable the site
echo "Enabling crypto.profithits.app site..."
sudo ln -sf /etc/nginx/sites-available/crypto.profithits.app /etc/nginx/sites-enabled/

# Test nginx configuration
echo "Testing nginx configuration..."
sudo nginx -t

# Reload nginx
echo "Reloading nginx..."
sudo systemctl reload nginx

echo "Nginx configuration for crypto.profithits.app completed!"
echo "Site should be accessible at: http://crypto.profithits.app"