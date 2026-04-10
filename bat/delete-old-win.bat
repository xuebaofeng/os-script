$targets = @(
"D:\Program Files",
"D:\Program Files (x86)",
"D:\ProgramData",
"D:\$RECYCLE.BIN",
"D:\Users",
"D:\System Volume Information",
"D:\Windows"
)

foreach ($t in $targets) {
    if (Test-Path $t) {
        Write-Host "处理: $t"

        # 1. 夺取所有权
        takeown /f $t /r /d y | Out-Null

        # 2. 授权管理员完全控制
        icacls $t /grant administrators:F /t /c /q | Out-Null

        # 3. 删除
        Remove-Item $t -Recurse -Force -ErrorAction SilentlyContinue
    }
}