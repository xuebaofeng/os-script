chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
# =========================
# 配置
# =========================

$targetHeight = 720
$targetFps = $null

# 可选:
# "amf"  = AMD硬件编码（快）
# "x265" = CPU软件编码（高质量）
$encoderMode = "amf"

# ===== AMF =====
$amfPreset = "quality"
$amfQp = 23

# ===== x265 =====
$x265Preset = "medium"
$x265Crf = 24

# 是否覆盖输出
$overwrite = $true

# 支持的视频扩展名
$videoExts = @(".mp4", ".mov", ".mkv")

$sourceFolder = "C:\shared\lexi-rage"

# =========================
# ffprobe函数
# =========================

function Get-VideoInfo {
    param (
        [string]$path
    )

    try {

        $result = ffprobe `
            -v error `
            -select_streams v:0 `
            -show_entries stream=codec_name,width,height `
            -of csv=p=0 `
            "$path"

        $parts = $result -split ","

        if ($parts.Length -ge 3) {

            return @{
                codec = $parts[0].Trim().ToLower()
                width  = [int]$parts[1]
                height = [int]$parts[2]
            }
        }
    }
    catch {

        Write-Host "FFprobe failed: $path"
    }

    return $null
}

# =========================
# 主程序
# =========================

Get-ChildItem -Path $sourceFolder -File | Where-Object {
    $videoExts -contains $_.Extension.ToLower()
} | ForEach-Object {

    $inputFile = $_.FullName

    # 输出文件后缀
    $suffix = "_${targetHeight}p"

    if ($encoderMode -eq "amf") {
        $suffix += "_amf"
    }
    else {
        $suffix += "_x265"
    }

    $outputFile = Join-Path -Path $_.DirectoryName -ChildPath "$($_.BaseName)$suffix.mp4"

    # =========================
    # 跳过检查
    # =========================

    $skip = $false

    if (Test-Path $outputFile) {

        $info = Get-VideoInfo $outputFile

        if ($info) {

            if (
            $info.codec -eq "hevc" `
                -and $info.height -eq $targetHeight
            ) {

                Write-Host "Skip: $($_.Name)"
                $skip = $true
            }
        }
    }

    if ($skip) {
        return
    }

    # =========================
    # 构建ffmpeg参数
    # =========================

    Write-Host ""
    Write-Host "=================================================="
    Write-Host "Processing: $($_.Name)"
    Write-Host "Mode: $encoderMode"

    $vf = "scale=-2:$targetHeight"

    $args = @()

    $args += "-hide_banner"
    $args += "-nostdin"

    if ($overwrite) {
        $args += "-y"
    }

    $args += "-i"
    $args += $inputFile

    $args += "-vf"
    $args += $vf

    # FPS
    if ($targetFps) {

        $args += "-r"
        $args += "$targetFps"
    }

    # =========================
    # AMD AMF
    # =========================

    if ($encoderMode -eq "amf") {

        $args += "-c:v"
        $args += "hevc_amf"

        $args += "-preset"
        $args += $amfPreset

        $args += "-rc"
        $args += "cqp"

        $args += "-qp_i"
        $args += "$amfQp"

        $args += "-qp_p"
        $args += "$amfQp"
    }

    # =========================
    # x265
    # =========================

    elseif ($encoderMode -eq "x265") {

        $args += "-c:v"
        $args += "libx265"

        $args += "-preset"
        $args += $x265Preset

        $args += "-crf"
        $args += "$x265Crf"
    }

    else {

        Write-Host "错误: encoderMode必须是 amf 或 x265"
        return
    }

    # 音频复制
    $args += "-c:a"
    $args += "copy"

    $args += $outputFile

    # =========================
    # 执行
    # =========================

    Write-Host ""
    Write-Host "ffmpeg $($args -join ' ')"
    Write-Host ""

    & ffmpeg @args

    if ($LASTEXITCODE -eq 0) {

        Write-Host ""
        Write-Host "Done: $(Split-Path $outputFile -Leaf)"
    }
    else {

        Write-Host ""
        Write-Host "FAILED: $($_.Name)"
    }
}

Write-Host ""
Write-Host "全部完成"