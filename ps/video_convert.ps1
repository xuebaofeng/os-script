# ===== 可配置参数 =====
$targetHeight = 720      # 想改成 1080 / 720 / 480 都可以
$targetFps = $null       # 设成 30 就强制30fps；设成 $null 就保持原帧率

Get-ChildItem -File | Where-Object { $_.Extension.ToLower() -in ".mp4",".mov" } | ForEach-Object {
    $in = $_.FullName

    # 输出文件名逻辑
    if ($_.BaseName -match "_${targetHeight}p$") {
        $out = $in
    } else {
        $out = "$($_.DirectoryName)\$($_.BaseName)_${targetHeight}p.mp4"
    }

    $skip = $false

    if (Test-Path $out) {
        try {
            $vinfo = ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height -of csv=p=0 "$out"
            $parts = $vinfo -split ","

            if ($parts.Length -ge 3) {
                $codec = $parts[0].Trim().ToLower()
                $width = [int]$parts[1]
                $height = [int]$parts[2]

                if ($codec -eq "hevc" -and $height -eq $targetHeight) {
                    Write-Host "Skip (already HEVC ${targetHeight}p): $($_.Name)"
                    $skip = $true
                }
            }
        } catch {
            Write-Host "FFprobe failed for $($_.Name), skipping check."
        }
    }

    if (-not $skip) {
        Write-Host "Processing: $($_.Name)"

        $vf = "scale=-2:$targetHeight"

        $fpsArg = @()
        if ($targetFps) {
            $fpsArg = @("-r", "$targetFps")
        }

        ffmpeg -y -i "$in" `
            -vf $vf `
            @fpsArg `
            -c:v libx265 -preset slow -crf 28 `
            -c:a copy `
            "$out"
    }
}