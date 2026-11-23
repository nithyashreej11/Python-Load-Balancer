import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("127.0.0.1", 9001))
server.listen()
print("Server listening on 127.0.0.1:9001")

conn, addr = server.accept()
data = conn.recv(1024).decode()
print("Received:", data, "from", addr)
conn.sendall(("Hello back: " + data).encode())

conn.close()
server.close()