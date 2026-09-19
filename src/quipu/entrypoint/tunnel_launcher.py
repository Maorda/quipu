# dantesito/quipu/entrypoint/tunnel_launcher.py
import os
import time
import sys
from pyngrok import ngrok

def load_env_manually():
    """Lee físicamente el archivo .env desde el disco para romper la caché de Windows."""
    token = ""
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("NGROK_AUTHTOKEN"):
                    try:
                        token = line.split("=")[1].strip()
                    except Exception:
                        pass
    return token

def start_tunnel():
    url = None
    try:
        print("🔍 Buscando NGROK_AUTHTOKEN de forma directa en el almacenamiento físico...")
        ngrok_token = load_env_manually()
        
        if not ngrok_token:
            ngrok_token = os.environ.get("NGROK_AUTHTOKEN", "").strip()

        if not ngrok_token:
            print("🚨 ERROR CRÍTICO: No se encuentra 'NGROK_AUTHTOKEN' configurado en su archivo .env")
            return

        # Autenticar la sesión del agente pyngrok en el entorno virtual
        ngrok.set_auth_token(ngrok_token)

        # Abrir el túnel HTTP encriptado hacia tu API de FastAPI local
        url = ngrok.connect(8000).public_url
        print(f"\n=======================================================================")
        print(f"🔓 URL PÚBLICA SEGURA DE NGROK: {url}")
        print(f"=======================================================================")
        print("📌 Copie la URL de arriba para enviar sus expedientes de forma remota.")
        print("📌 Mantenga esta ventana abierta para recibir peticiones.")
        print("📌 Presione Ctrl + C para apagar el servidor de forma segura.\n")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Cerrando túneles de red de ngrok de forma segura...")
        if url:
            try:
                ngrok.disconnect(url)
            except Exception:
                # Si Windows ya cerró el socket, ignora el fallo de red de forma limpia
                pass
        print("✅ Conexiones cerradas.")
    except Exception as exc:
        print(f"❌ Error crítico en el túnel de pyngrok: {exc}")

if __name__ == "__main__":
    start_tunnel()
