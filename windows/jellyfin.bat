@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set EXE="C:\green\jellyfin\jellyfin.exe"

echo 启动 Jellyfin...
start "" %EXE%

:: 计算结束时间（当前时间 + 30分钟）
for /f "tokens=1-4 delims=:.," %%a in ("%time%") do (
    set /a start=%%a*3600+%%b*60+%%c
)

set /a end=start+1800

echo.
echo ===== 30分钟倒计时 =====

:loop
for /f "tokens=1-4 delims=:.," %%a in ("%time%") do (
    set /a now=%%a*3600+%%b*60+%%c
)

set /a remain=end-now

if !remain! LEQ 0 goto done

set /a min=!remain!/60
set /a sec=!remain!%%60

if !sec! LSS 10 set sec=0!sec!

cls
echo Jellyfin 运行中...
echo 剩余时间: !min!:!sec!

ping 127.0.0.1 -n 2 >nul
goto loop

:done

echo 时间到，正在关闭 Jellyfin...

taskkill /F /IM jellyfin.exe >nul 2>&1
net stop JellyfinServer >nul 2>&1

echo 已关闭
pause