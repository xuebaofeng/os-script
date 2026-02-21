# ============================================================
# PowerShell: 确保 Microsoft Family Safety 服务正常运行
# 说明：启动关键服务并设置为自动
# 需管理员权限运行
# ============================================================

# 核心服务列表
$msfsServices = @(
    "wlidsvc",       # Microsoft Account Sign-in Assistant
    "WpcMonSvc"     # Windows Parental Controls Monitor Service
)

foreach (${svc} in $msfsServices) {
    Try {
        # 设置开机自启
        Set-Service -Name $svc -StartupType Automatic
        # 启动服务
        Start-Service -Name $svc -ErrorAction SilentlyContinue
        Write-Output "Service ${svc}: Started and set to Automatic."
    } Catch {
        Write-Output "Service ${svc}: Could not modify or start. $_"
    }
}

Write-Output "=== Service Status Check ==="

foreach ($svc in $msfsServices) {
    Try {
        $service = Get-Service -Name $svc -ErrorAction Stop
        Write-Output ("Service {0}: Status = {1}, StartupType = {2}" -f `
            $service.Name, `
            $service.Status, `
            (Get-CimInstance Win32_Service -Filter "Name='$svc'").StartMode)
    } Catch {
        Write-Output "Service ${svc}: Not found or inaccessible."
    }
}