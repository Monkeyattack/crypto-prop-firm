#!/usr/bin/env python3
"""
Setup script for Crypto Paper Trading System
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path
from config import Config

def run_command(command, description="", check=True):
    """Run a command and handle errors"""
    print(f"🔄 {description or command}")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(f"✅ Output: {result.stdout.strip()}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False

def setup_virtual_environment():
    """Setup Python virtual environment"""
    print("\n📦 Setting up virtual environment...")
    
    if not os.path.exists("venv"):
        if not run_command("python -m venv venv", "Creating virtual environment"):
            print("❌ Failed to create virtual environment")
            return False
    else:
        print("✅ Virtual environment already exists")
    
    # Activate venv and install requirements
    if sys.platform == "win32":
        activate_cmd = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
    else:
        activate_cmd = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
    
    print("📦 Installing requirements...")
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installing Python packages"):
        print("❌ Failed to install requirements")
        return False
    
    return True

def setup_environment_file():
    """Setup .env file from template"""
    print("\n⚙️ Setting up environment configuration...")
    
    if not os.path.exists(".env"):
        if os.path.exists(".env.template"):
            import shutil
            shutil.copy(".env.template", ".env")
            print("✅ Created .env from template")
            print("⚠️  Please edit .env file with your actual configuration values")
        else:
            print("❌ .env.template not found")
            return False
    else:
        print("✅ .env file already exists")
    
    return True

def setup_database():
    """Initialize database"""
    print("\n🗄️ Setting up database...")
    
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        print("✅ Database initialized successfully")
        
        # Test database connection
        stats = db.get_performance_stats()
        print(f"✅ Database test successful - Initial capital: ${db.get_current_capital():.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def setup_logging():
    """Setup logging directory"""
    print("\n📝 Setting up logging...")
    
    log_dir = Path(Config.LOG_FILE).parent
    log_dir.mkdir(exist_ok=True)
    
    print(f"✅ Log directory created: {log_dir}")
    return True

def setup_nginx_config():
    """Generate nginx configuration"""
    print("\n🌐 Generating nginx configuration...")
    
    nginx_config = f"""# Crypto Paper Trading System - Nginx Configuration
# Add this to your nginx sites-available directory

server {{
    listen 80;
    server_name your-domain.com;  # Change this to your domain
    
    # Streamlit Dashboard
    location / {{
        proxy_pass http://localhost:{Config.STREAMLIT_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    # n8n Workflow Engine
    location /n8n/ {{
        proxy_pass http://localhost:{Config.N8N_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    # Health check endpoint
    location /health {{
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }}
}}

# SSL/HTTPS configuration (uncomment when ready)
# server {{
#     listen 443 ssl http2;
#     server_name your-domain.com;
#     
#     ssl_certificate /path/to/your/certificate.crt;
#     ssl_certificate_key /path/to/your/private.key;
#     
#     # Include the location blocks from above
# }}
"""
    
    with open("nginx.conf.example", "w") as f:
        f.write(nginx_config)
    
    print("✅ Nginx configuration saved to nginx.conf.example")
    return True

def setup_systemd_service():
    """Generate systemd service file"""
    print("\n⚙️ Generating systemd service configuration...")
    
    current_dir = os.path.abspath(".")
    user = os.getenv("USER", "www-data")
    
    service_config = f"""[Unit]
Description=Crypto Paper Trading Dashboard
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={current_dir}
Environment=PATH={current_dir}/venv/bin
ExecStart={current_dir}/venv/bin/streamlit run dashboard/app.py --server.port {Config.STREAMLIT_PORT} --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    with open("crypto-paper-trading.service", "w") as f:
        f.write(service_config)
    
    print("✅ Systemd service file saved to crypto-paper-trading.service")
    print("   To install: sudo cp crypto-paper-trading.service /etc/systemd/system/")
    print("   Then: sudo systemctl enable crypto-paper-trading && sudo systemctl start crypto-paper-trading")
    return True

def run_tests():
    """Run basic tests"""
    print("\n🧪 Running tests...")
    
    try:
        # Test signal processor
        from signal_processor import SignalProcessor
        processor = SignalProcessor()
        
        test_message = """
        Buy BTCUSDT
        Entry: 45000
        TP: 47000
        SL: 43000
        """
        
        result = processor.parse_signal(test_message)
        if result:
            print("✅ Signal parsing test passed")
        else:
            print("❌ Signal parsing test failed")
            return False
        
        # Test database
        from database import DatabaseManager
        db = DatabaseManager()
        stats = db.get_performance_stats()
        print("✅ Database test passed")
        
        # Test configuration
        Config.validate_config()
        print("✅ Configuration validation passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        return False

def print_next_steps():
    """Print next steps for user"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print("\nNext Steps:")
    print("1. Edit .env file with your actual configuration")
    print("2. Start the dashboard:")
    if sys.platform == "win32":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print(f"   streamlit run dashboard/app.py --server.port {Config.STREAMLIT_PORT}")
    print("\n3. Start n8n (in another terminal):")
    print(f"   n8n --port {Config.N8N_PORT}")
    print("\n4. Access the dashboard:")
    print(f"   http://localhost:{Config.STREAMLIT_PORT}")
    print("\n5. Import the n8n workflow:")
    print("   - Go to n8n interface")
    print("   - Import n8n_workflow_sqlite.json")
    print("\n6. For production deployment:")
    print("   - Review nginx.conf.example")
    print("   - Review crypto-paper-trading.service")
    print("   - Setup SSL certificates")
    print("\n📚 Check README.md for detailed usage instructions")

def main():
    """Main setup function"""
    print("🚀 Crypto Paper Trading System Setup")
    print("====================================")
    
    success = True
    
    # Run setup steps
    steps = [
        setup_virtual_environment,
        setup_environment_file,
        setup_logging,
        setup_database,
        setup_nginx_config,
        setup_systemd_service,
        run_tests
    ]
    
    for step in steps:
        if not step():
            success = False
            break
    
    if success:
        print_next_steps()
    else:
        print("\n❌ Setup failed. Please check the errors above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()