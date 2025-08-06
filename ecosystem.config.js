module.exports = {
  apps: [
    {
      name: 'crypto-dashboard',
      script: './start_dashboard.sh',
      cwd: '/root/crypto-paper-trading',
      interpreter: 'bash',
      env: {
        PYTHONPATH: '/root/crypto-paper-trading'
      }
    },
    {
      name: 'signal-monitor',
      script: 'automated_signal_monitor.py',
      cwd: '/root/crypto-paper-trading',
      interpreter: '/root/crypto-paper-trading/venv/bin/python',
      env: {
        PYTHONPATH: '/root/crypto-paper-trading'
      },
      restart_delay: 5000,
      max_restarts: 10,
      autorestart: true
    },
    {
      name: 'position-monitor',
      script: 'position_monitor.py',
      cwd: '/root/crypto-paper-trading',
      interpreter: '/root/crypto-paper-trading/venv/bin/python',
      env: {
        PYTHONPATH: '/root/crypto-paper-trading'
      },
      restart_delay: 5000,
      max_restarts: 10,
      autorestart: true
    }
  ]
}