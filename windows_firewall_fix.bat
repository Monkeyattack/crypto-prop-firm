@echo off
echo ============================================================
echo FIXING WINDOWS FIREWALL AND PERMISSIONS FOR MT5
echo ============================================================
echo.
echo This script needs to run as Administrator.
echo.
echo Adding Python and MT5 to Windows Firewall exceptions...
echo.

netsh advfirewall firewall add rule name="Python MT5" dir=in action=allow program="C:\Program Files\Python312\python.exe" enable=yes
netsh advfirewall firewall add rule name="Python MT5 Out" dir=out action=allow program="C:\Program Files\Python312\python.exe" enable=yes
netsh advfirewall firewall add rule name="MT5 Terminal" dir=in action=allow program="C:\Program Files\MetaTrader 5\terminal64.exe" enable=yes
netsh advfirewall firewall add rule name="MT5 Terminal Out" dir=out action=allow program="C:\Program Files\MetaTrader 5\terminal64.exe" enable=yes

echo.
echo Firewall rules added.
echo.
echo Now testing MT5 connection...
echo.

cd /d C:\Users\cmeredith\source\repos\crypto-prop-firm
python connect_to_plexy.py

pause