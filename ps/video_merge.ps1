Get-ChildItem *.mp4 | Sort-Object Name | ForEach-Object { "file '$($_.FullName)'" } | Set-Content list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp4