rem https://my.vmware.com/web/vmware/free#desktop_end_user_computing/vmware_workstation_player/12_0|PLAYER-1200|drivers_tools
cd %USERPROFILE%

vmrun suspend Downloads\DEV3.0\DEV3.0.vmx

@echo off

set mydate=%date:~6,4%-%date:~3,2%-%date:~0,2%
echo %mydate%

robocopy Downloads\DEV3.0 g:\backup\vm\%mydate% /xf *.log *.lock *.vmem *.gz *.dmp *.vmss *.vmxf *.vmsd
pause