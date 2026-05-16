@echo off
cd /d C:\Users\a.moustaine\Downloads\gestion_stock
start "FlaskServer" /min python app.py
timeout /t 2 >nul
start http://127.0.0.1:5000
echo.
echo Appuyez sur une touche pour arrêter le serveur et fermer le navigateur...
pause >nul
taskkill /im python.exe /f
taskkill /im msedge.exe /f   