rem https://my.vmware.com/web/vmware/free#desktop_end_user_computing/vmware_workstation_player/12_0|PLAYER-1200|drivers_tools

cd %HOMEPATH%
vmrun suspend Downloads\Bizx2.0.1-b1602a\Bizx2.0.vmx


@echo off
For /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
echo %mydate%

robocopy Downloads\Bizx2.0.1-b1602a Downloads\%mydate%
pause