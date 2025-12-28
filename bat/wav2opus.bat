cd c:\baidunetdiskdownload
@echo off
REM 批量将当前文件夹下所有 WAV 转为 Opus
REM 输出文件放在同名 .opus

for %%f in (*.wav) do (
    echo 正在转换 %%f ...
    ffmpeg -y -i "%%f" -c:a libopus -b:a 96k "%%~nf.opus"
)
echo 全部转换完成！
pause