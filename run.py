import socket
import threading
import time
import webbrowser
import uvicorn

from main import app


PORT = 8000
HOST = "127.0.0.1"


def is_port_in_use(port):
    """
    Verifica si el puerto ya está ocupado
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, port)) == 0


def open_browser():
    """
    Espera un poco y abre el navegador
    """
    time.sleep(1.5)
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":

    if is_port_in_use(PORT):

        print("Servidor ya iniciado.")
        webbrowser.open(f"http://{HOST}:{PORT}")

    else:

        print("Iniciando servidor...")

        # Abrir navegador en segundo plano
        threading.Thread(target=open_browser).start()

        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
            access_log=False,
            log_config=None
        )