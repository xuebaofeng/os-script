@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

taskkill /IM portmaster.exe /F
start "" "C:\Program Files\Portmaster\portmaster.exe"