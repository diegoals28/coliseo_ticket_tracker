@echo off
chcp 65001 > nul
echo.
echo ======================================================================
echo 🏛️  COLOSSEO MONITOR - Iniciando aplicación web
echo ======================================================================
echo.
echo 📋 La aplicación se abrirá en tu navegador
echo 🌐 URL: http://localhost:5000
echo.
echo ⚠️  Para detener el servidor, presiona CTRL+C
echo ======================================================================
echo.

python app.py

pause
