# ===============================================
# 💀 一键彻底禁用 Windows OneDrive
# ===============================================

Write-Host "🔹 正在停止 OneDrive 进程..."
Get-Process OneDrive -ErrorAction SilentlyContinue | Stop-Process -Force

# ===============================================
# 删除用户目录残留
# ===============================================
Write-Host "🔹 删除用户目录残留..."
Get-ChildItem C:\Users -Directory | ForEach-Object {
    $u=$_
    $paths=@(
        "$($u.FullName)\OneDrive",
        "$($u.FullName)\AppData\Local\Microsoft\OneDrive",
        "$($u.FullName)\AppData\Local\OneDriveTemp",
        "$($u.FullName)\AppData\Roaming\Microsoft\OneDrive"
    )
    foreach($p in $paths){
        if(Test-Path $p){ Remove-Item -Path $p -Recurse -Force -ErrorAction SilentlyContinue; Write-Host "✅ 删除: $p" }
    }
}

# ===============================================
# 删除系统目录残留
# ===============================================
Write-Host "🔹 删除系统残留..."
$systemPaths=@("C:\OneDriveTemp")
foreach($p in $systemPaths){
    if(Test-Path $p){ Remove-Item -Path $p -Recurse -Force -ErrorAction SilentlyContinue; Write-Host "✅ 删除: $p" }
}


# ===============================================
# 禁止 OneDrive 自动启动
# ===============================================
Write-Host "🔹 禁止 OneDrive 自动启动..."
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "OneDrive" /f

# ===============================================
# 注册表防护阻止未来安装/同步
# ===============================================
Write-Host "🔹 修改注册表防止重新安装..."
$regPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\OneDrive"
if(-not (Test-Path $regPath)){ New-Item -Path $regPath -Force | Out-Null }
Set-ItemProperty -Path $regPath -Name "DisableFileSyncNGSC" -Type DWord -Value 1
Write-Host "✅ 注册表修改完成"

# ===============================================
# 重命名 System32 中 OneDriveSetup.exe
# ===============================================
Write-Host "🔹 阻止 System32 OneDrive 文件运行..."
$sys32 = "$env:SystemRoot\System32\OneDriveSetup.exe"
if(Test-Path $sys32){
    takeown /f $sys32 /a
    icacls $sys32 /grant Administrators:F
    Rename-Item -Path $sys32 -NewName "OneDriveSetup.exe.disabled"
    Write-Host "✅ System32 OneDriveSetup.exe 已重命名"
}

# ===============================================
# 重命名 WinSxS 中 OneDriveSetup.exe
# ===============================================
Write-Host "🔹 阻止 WinSxS OneDrive 文件运行..."
Get-ChildItem "C:\Windows\WinSxS" -Recurse -Include OneDriveSetup.exe | ForEach-Object {
    try {
        takeown /f $_.FullName /a
        icacls $_.FullName /grant Administrators:F
        Rename-Item -Path $_.FullName -NewName "$($_.Name).disabled"
        Write-Host "✅ 已重命名: $($_.FullName)"
    } catch {
        Write-Host "❌ 无法重命名: $($_.FullName) - $_"
    }
}

# ===============================================
# 完成提示
# ===============================================
Write-Host "🎉 OneDrive 已彻底禁用！请重启系统以完全生效。"