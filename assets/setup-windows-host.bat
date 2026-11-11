@echo off
:: ==============================================================================
:: WSL2 AGY Dual-Display System - Windows Host One-Click Setup Script
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
echo [1/3] Detecting WSL2 Internal Virtual IP...
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
echo [2/3] Configuring Windows PortProxy (netsh)...
echo ==============================================================================
netsh interface portproxy delete v4tov4 listenport=%SSH_PORT% listenaddress=0.0.0.0 >nul 2>&1
netsh interface portproxy add v4tov4 listenport=%SSH_PORT% listenaddress=0.0.0.0 connectport=22 connectaddress=%WSL_IP%

echo ==============================================================================
echo [3/3] Adding Windows Defender Inbound Firewall Rule...
echo ==============================================================================
netsh advfirewall firewall delete rule name="WSL KeyBridge SSH (%SSH_PORT%)" >nul 2>&1
netsh advfirewall firewall add rule name="WSL KeyBridge SSH (%SSH_PORT%)" dir=in action=allow protocol=TCP localport=%SSH_PORT% >nul

echo ==============================================================================
echo [SUCCESS] Windows Host PortProxy and Firewall configuration complete!
echo KeyBridge mobile app can now connect directly via port %SSH_PORT%.
echo ==============================================================================
pause
