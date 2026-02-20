# ================================
# 自动提权检查
# ================================
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Host "Script is not running as administrator. Restarting with elevated privileges..."
    # 使用 RunAs 提权重新启动自己
    Start-Process powershell "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "=========================="
Write-Host "Starting automatic Windows cleanup with admin privileges"
Write-Host "=========================="

# --------------------------
# 1. 清理用户临时文件
# --------------------------
$temp = $env:TEMP
Write-Host "Cleaning user temp files: $temp"
Get-ChildItem -Path $temp -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# --------------------------
# 2. 清理 Windows 临时文件
# --------------------------
$winTemp = "C:\Windows\Temp"
Write-Host "Cleaning system temp files: $winTemp"
Get-ChildItem -Path $winTemp -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# --------------------------
# 3. 清理 Windows 更新缓存
# --------------------------
Write-Host "Stopping Windows Update service..."
Stop-Service wuauserv -Force
$updateCache = "C:\Windows\SoftwareDistribution\Download"
Write-Host "Cleaning Windows Update cache: $updateCache"
Get-ChildItem -Path $updateCache -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# --------------------------
# 4. 清空回收站
# --------------------------
Write-Host "Emptying Recycle Bin..."
Clear-RecycleBin -Force -ErrorAction SilentlyContinue

# --------------------------
# 5. 清理浏览器缓存 (Edge, Chrome, Firefox)
# --------------------------
$browserCaches = @(
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cache",
    "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache",
    "$env:APPDATA\Mozilla\Firefox\Profiles\*.*\cache2"
)
foreach ($cache in $browserCaches) {
    if (Test-Path $cache) {
        Write-Host "Cleaning browser cache: $cache"
        Get-ChildItem -Path $cache -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# --------------------------
# 6. 自动删除所有旧系统还原点
# --------------------------
Write-Host "Deleting all old system restore points..."
vssadmin delete shadows /all /quiet

Write-Host "=========================="
Write-Host "Automatic cleanup completed. Ready for backup."
Write-Host "=========================="
pause