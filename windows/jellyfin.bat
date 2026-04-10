@echo off
chcp 65001 >nul

set EXE="C:\Program Files\Jellyfin\Server\jellyfin.exe"
set /a total=1800

echo 启动 Jellyfin...
start "" %EXE%

echo.
echo ===== 30分钟倒计时 =====

:loop
if %total% LEQ 0 goto done

set /a min=total/60
set /a sec=total%%60

if %sec% LSS 10 set sec=0%sec%

cls
echo Jellyfin 运行中...
echo 剩余时间: %min%:%sec%

timeout /t 1 >nul
set /a total-=1
goto loop

:done

echo 时间到，正在关闭 Jellyfin...

taskkill /F /IM jellyfin.exe >nul 2>&1
taskkill /F /IM dotnet.exe >nul 2>&1
taskkill /F /IM Jellyfin.Server.exe >nul 2>&1
net stop JellyfinServer >nul 2>&1

echo 已关闭
pause