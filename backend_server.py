import socket
import sys

HOST = "127.0.0.1"


def run_server(name, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, port))
    server.listen()
    print(f"[{name}] Listening on {HOST}:{port}")

    try:
        while True:
            conn, addr = server.accept()
            with conn:
                data = conn.recv(1024).decode()
                if not data:
                    continue  # empty connection (e.g. a health check)
                print(f"[{name}] Received '{data}' from {addr}")
                reply = f"{name} handled: {data}"
                conn.sendall(reply.encode())
    except KeyboardInterrupt:
        print(f"\n[{name}] Shutting down")
    finally:
        server.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python backend_server.py <name> <port>")
        sys.exit(1)
    run_server(sys.argv[1], int(sys.argv[2]))
    