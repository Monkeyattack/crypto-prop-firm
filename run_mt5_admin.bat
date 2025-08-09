@echo off
echo Running MT5 Connection with Admin Rights...
echo.
echo This will help resolve IPC timeout issues.
echo.
cd /d C:\Users\cmeredith\source\repos\crypto-prop-firm
"C:\Program Files\Python312\python.exe" verify_mt5_credentials.py
pause