"""Proxy TCP: expõe o Ollama do host (127.0.0.1:11434) aos containers.

Motivo: o serviço ollama.service escuta apenas em 127.0.0.1:11434 e o
override para 0.0.0.0 exige sudo (sem NOPASS nesta máquina). Este proxy
escuta em 0.0.0.0:11435 (sem root, porta > 1024) e encaminha tudo para
127.0.0.1:11434. Os containers usam http://host.docker.internal:11435.

Persistência: backend/scripts/ollama-proxy.service (systemd --user).
Correção permanente (com sudo, quando possível):
  sudo mkdir -p /etc/systemd/system/ollama.service.d
  echo -e '[Service]\\nEnvironment="OLLAMA_HOST=0.0.0.0:11434"' \\
    | sudo tee /etc/systemd/system/ollama.service.d/override.conf
  sudo systemctl daemon-reload && sudo systemctl restart ollama
Depois disso, apontar OLLAMA_BASE_URL de volta para :11434 e desativar o proxy.
"""

import socket
import threading

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 11435
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 11434
BUF = 65536


def pipe(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(BUF)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def handle(client: socket.socket) -> None:
    client.settimeout(None)  # resposta pode demorar minutos (CPU, stream=false)
    try:
        upstream = socket.create_connection((TARGET_HOST, TARGET_PORT), timeout=10)
        upstream.settimeout(None)  # create_connection herda o timeout; limpar!
    except OSError:
        client.close()
        return
    t = threading.Thread(target=pipe, args=(upstream, client), daemon=True)
    t.start()
    pipe(client, upstream)
    t.join()


def main() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((LISTEN_HOST, LISTEN_PORT))
    srv.listen(100)
    print(f"ollama-proxy: {LISTEN_HOST}:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}",
          flush=True)
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
