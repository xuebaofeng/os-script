@echo off
chcp 936 >nul
title Remove Baidu Netdisk ImageViewer
echo ==========================================
echo Remove Baidu Netdisk "Smart Image Viewer"
echo ==========================================
echo.
echo Please run this script as Administrator
echo.
pause

echo Killing related processes...
taskkill /f /im BaiduNetdisk.exe >nul 2>&1
taskkill /f /im BaiduNetdiskImageViewer.exe >nul 2>&1
timeout /t 2 >nul

echo Deleting registry keys...
reg delete "HKEY_CLASSES_ROOT\BaiduNetdiskImageViewerAssociations" /f >nul 2>&1
reg delete "HKEY_CURRENT_USER\Software\Baidu\BaiduNetdiskImageViewer" /f >nul 2>&1
reg delete "HKEY_CURRENT_USER\Software\RegisteredApplications" /v "BaiduNetdiskImageViewer" /f >nul 2>&1

echo Deleting ImageViewer folders...
if exist "%APPDATA%\baidu\BaiduNetdisk\module\ImageViewer" (
    rd /s /q "%APPDATA%\baidu\BaiduNetdisk\module\ImageViewer"
    echo Deleted: %%APPDATA%%\baidu\BaiduNetdisk\module\ImageViewer
)

for %%i in (
    "%ProgramFiles%\Baidu\BaiduNetdisk"
    "%ProgramFiles(x86)%\Baidu\BaiduNetdisk"
    "%LOCALAPPDATA%\Baidu\BaiduNetdisk"
    "%APPDATA%\Baidu\BaiduNetdisk"
) do (
    if exist "%%i\module\ImageViewer" (
        rd /s /q "%%i\module\ImageViewer"
        echo Deleted: %%i\module\ImageViewer
    )
)

echo.
echo Done! Please restart your computer and check.
echo.
pause