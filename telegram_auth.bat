@echo off
echo ============================================================
echo TELEGRAM AUTHENTICATION SETUP
echo ============================================================
echo.
echo This will request a verification code from Telegram.
echo You'll need to enter it when prompted.
echo.
echo Press any key to continue...
pause > nul

python telegram_request_code.py

echo.
echo ============================================================
echo If authentication succeeded, you can now run:
echo python telegram_signal_collector.py
echo ============================================================
pause