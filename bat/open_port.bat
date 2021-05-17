@REM jellyfin
netsh advfirewall firewall add rule name="jellyfin TCP Port 8096" dir=in action=allow protocol=TCP localport=8096