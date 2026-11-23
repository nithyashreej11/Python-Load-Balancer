import socket
import sys

port = int(sys.argv[1])
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", port))
client.sendall("request-1".encode())
print("Client got:", client.recv(1024).decode())
client.close()