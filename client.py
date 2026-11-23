import socket
import sys

LB_HOST = "127.0.0.1"
LB_PORT = 9000


def send_request(message, host=LB_HOST, port=LB_PORT, timeout=5):
    """Open a TCP connection, send one message, return the reply text."""
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(message.encode())
        return sock.recv(1024).decode()


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    port = int(sys.argv[2]) if len(sys.argv) > 2 else LB_PORT

    for i in range(1, count + 1):
        message = f"request-{i}"
        try:
            reply = send_request(message, port=port)
            if not reply:
                reply = "(empty reply)"
            print(f"Sent {message:<12} -> reply: {reply}")
        except ConnectionRefusedError:
            print(f"Sent {message:<12} -> FAILED: nothing is listening on port {port}")
        except TimeoutError:
            print(f"Sent {message:<12} -> FAILED: timed out")
        except OSError as error:
            print(f"Sent {message:<12} -> FAILED: {error}")


if __name__ == "__main__":
    main()