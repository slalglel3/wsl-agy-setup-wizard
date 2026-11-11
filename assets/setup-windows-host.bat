@echo off
:: ==============================================================================
:: WSL2 AGY Dual-Display System - Windows Host One-Click Setup Script v2
:: Must be executed as Administrator!
:: ==============================================================================

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator!
    echo Right-click this file and select 'Run as administrator'.
    pause
    exit /b 1
)

set SSH_PORT={{ SSH_PORT }}
echo ==============================================================================
echo [1/4] Ensuring WSL OpenSSH Server is running...
echo ==============================================================================
wsl -u root service ssh status >nul 2>&1 || wsl -u root service ssh start >nul 2>&1

echo ==============================================================================
echo [2/4] Detecting WSL2 Internal Virtual IP...
echo ==============================================================================

for /f "tokens=1" %%i in ('wsl -e hostname -I 2^>nul') do set WSL_IP=%%i

if "%WSL_IP%"=="" (
    echo [ERROR] Failed to detect WSL IP! Is WSL running?
    pause
    exit /b 1
)

echo -> Detected WSL IP: %WSL_IP%
echo -> Forwarding Port: %SSH_PORT% -> WSL IP:22

echo ==============================================================================
echo [3/4] Configuring Windows PortProxy (netsh)...
echo ==============================================================================
netsh interface portproxy delete v4tov4 listenport=%SSH_PORT% listenaddress=0.0.0.0 >nul 2>&1
netsh interface portproxy add v4tov4 listenport=%SSH_PORT% listenaddress=0.0.0.0 connectport=22 connectaddress=%WSL_IP%

echo ==============================================================================
echo [4/4] Adding Windows Defender Inbound Firewall Rule...
echo ==============================================================================
netsh advfirewall firewall delete rule name="WSL KeyBridge SSH (%SSH_PORT%)" >nul 2>&1
netsh advfirewall firewall add rule name="WSL KeyBridge SSH (%SSH_PORT%)" dir=in action=allow protocol=TCP localport=%SSH_PORT% >nul

echo ==============================================================================
echo [SUCCESS] Windows Host PortProxy and Firewall configuration complete!
echo KeyBridge mobile app can now connect directly via port %SSH_PORT%.
echo.
echo [TIP] To keep PortProxy updated on Windows reboot, a Scheduled Task
echo can be registered to run this script at logon.
echo ==============================================================================
pause
