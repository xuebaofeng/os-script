
Get-ChildItem -File | Where-Object { $_.Extension.ToLower() -in ".mp4",".mov" } | ForEach-Object {
    $in = $_.FullName

    # 输出文件名逻辑
    if ($_.BaseName -match "_1080p$") {
        $out = $in  # 已经是 1080p 文件
    } else {
        $out = "$($_.DirectoryName)\$($_.BaseName)_1080p.mp4"
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

                if ($codec -eq "hevc" -and $width -eq 1920 -and $height -eq 1080) {
                    Write-Host "Skip (already HEVC 1080p): $($_.Name)"
                    $skip = $true
                }
            }
        } catch {
            Write-Host "FFprobe failed for $($_.Name), skipping check."
        }
    }

    if (-not $skip) {
        Write-Host "Processing: $($_.Name)"
        ffmpeg -y -i "$in" -vf scale=1920:-2 -r 30 -c:v libx265 -preset slow -crf 24 -c:a copy "$out"
    }
}