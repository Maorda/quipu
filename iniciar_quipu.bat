@echo off
chcp 65001 >nul
TITLE Orquestador Quipu - Control de Servicios Remotos
COLOR 0A

cd /d "%~dp0"

echo =======================================================================
echo 🚀 INICIALIZANDO INFRAESTRUCTURA (FASTAPI + NGROK)
echo =======================================================================
echo.

if not exist ".env" (
    echo 🚨 ERROR CRITICO: No se encuentra el archivo .env en la raiz del proyecto.
    pause
    exit /b 1
)

if not exist "venv\Scripts\activate.bat" (
    echo 🚨 ERROR CRITICO: No se encuentra el entorno virtual en la ruta venv\
    pause
    exit /b 1
)

echo ⚙️ [1/2] Lanzando Microservicio FastAPI...
:: APUNTAMOS EL PYTHONPATH A LA CARPETA SRC
set PYTHONPATH=src
start "Quipu FastAPI Backend" cmd /k "call venv\Scripts\activate.bat && python -m uvicorn quipu.entrypoint.api_server:app --host 127.0.0.1 --port 8000 --env-file .env"
echo ✅ Servidor FastAPI inicializando en ventana independiente...
echo.

echo ⚙️ Esperando 4 segundos para la apertura del socket de red...
timeout /t 4 /nobreak >nul
echo.

echo ⚙️ [2/2] Abriendo tunel publico seguro via pyngrok...
if exist "src\quipu\entrypoint\tunnel_launcher.py" (
    start "Quipu Ngrok Tunnel" cmd /k "call venv\Scripts\activate.bat && python src\quipu\entrypoint\tunnel_launcher.py"
    echo ✅ Tunel Ngrok inicializando en ventana independiente...
) else (
    echo 🚨 ERROR CRITICO: No se encontro tunnel_launcher.py.
    pause
    exit /b 1
)

exit