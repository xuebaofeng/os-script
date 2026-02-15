# 路径数组，包含可能的 Roblox 安装位置
$paths = @(
    "C:\Program Files (x86)\Roblox",
    "C:\Users\*\AppData\Local\Roblox"
)

foreach ($path in $paths) {
    try {
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Output "Deleted: $path"
    } catch {
        Write-Output "Failed to delete: $path"
    }
}
