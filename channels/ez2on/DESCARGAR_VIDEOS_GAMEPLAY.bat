@echo off
REM EZ2ON: videos de gameplay (480p, sin audio) para sincronizar los BGA. Se guardan en D:\EZ2ON_PIU\gameplay_video
cd /d D:\EZ2ON_PIU
yt-dlp -a videos_a_descargar.txt -f "bv*[height<=480][ext=mp4]/bv*[height<=480]" -o "gameplay_video/%%(id)s.%%(ext)s" --no-overwrites --sleep-interval 2
pause
