rem https://my.vmware.com/web/vmware/free#desktop_end_user_computing/vmware_workstation_player/12_0|PLAYER-1200|drivers_tools
cd c:\wbem

vmrun suspend DEV3.1.2\DEV3.1.2.vmx

@echo off

set mydate=%date:~-4%%date:~4,2%%date:~7,2%
echo %mydate%

robocopy DEV3.1.2 f:\backup\vm\%mydate% /xf *.log *.lock *.vmem *.gz *.dmp *.vmss *.vmxf *.vmsd
robocopy DEV3.1.2 g:\backup\vm\%mydate% /xf *.log *.lock *.vmem *.gz *.dmp *.vmss *.vmxf *.vmsd
pause