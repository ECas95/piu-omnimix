@echo off
REM EZ2ON: segunda tanda de videos de gameplay (480p, sin audio) para las canciones PROBABLE / REVISAR
cd /d D:\EZ2ON_PIU
yt-dlp -a videos_a_descargar2.txt -f "bv*[height<=480][ext=mp4]/bv*[height<=480]" -o "gameplay_video/%%(id)s.%%(ext)s" --no-overwrites --sleep-interval 2
pause
