reg add "HKCU\Control Panel\TimeDate\AdditionalClocks\1" /v Enable /t REG_DWORD /d 1 /f
reg add "HKCU\Control Panel\TimeDate\AdditionalClocks\1" /v DisplayName /t REG_SZ /d "China" /f
reg add "HKCU\Control Panel\TimeDate\AdditionalClocks\1" /v TzRegKeyName /t REG_SZ /d "China Standard Time" /f