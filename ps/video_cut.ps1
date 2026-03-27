# ====== 配置部分 ======
$input = "C:\BaiduNetdiskDownload\2012b-ecnl-rl-vs-stanford-strikers-fc-12b-2025-09-06.mov"

# 定义时间段数组（可以多个）
$clips = @(
    @{start="00:10:00"; end="00:49:55"},
    @{start="01:02:48"; end="01:44:30"}
)
# =====================

$dir  = Split-Path $input
$base = [System.IO.Path]::GetFileNameWithoutExtension($input)
$ext  = [System.IO.Path]::GetExtension($input)

$i = 1
foreach ($clip in $clips) {
    $start = $clip.start
    $end   = $clip.end
    $output = Join-Path $dir ("$base`_$i$ext")  # 输出文件名：原名_1.mp4, _2.mp4 ...

    if (Test-Path $output) {
        Write-Host "Skip (already exists): $output"
    } else {
        Write-Host "Processing: $input  =>  $output ($start - $end)"
        ffmpeg -ss $start -to $end -i "$input" -c copy "$output"
    }

    $i++
}