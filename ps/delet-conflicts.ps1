$path = "D:\shared"

Get-ChildItem -Path $path -Recurse -Force |
        Where-Object { $_.Name -like "*sync-conflict*" } |
        Remove-Item -Force -Recurse
