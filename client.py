import sys
import threading
import socket

from capchat_constants import PORT_NUMBER
from capchat_constants import BUFFER_SIZE

inputPrompt = ""

def clientSendThread(clientSocket:socket.socket):
  while True:
    print(inputPrompt, end="")
    message = input()
    # Find a way to overwrite previous line
    message = message[0:BUFFER_SIZE - 1]
    clientSocket.send(message.encode())

def clientReceiveThread(clientSocket:socket.socket):
  while True:
    message = clientSocket.recv(BUFFER_SIZE).decode()
    # Find a way to overwrite previous line
    print(message)
    print(inputPrompt, end="")

if __name__ =="__main__":
  if not len(sys.argv) == 3:
    print("Usage: python3 client.py <server ip address> <username>")
    exit(1)

  serverIP = sys.argv[1]
  username = sys.argv[2]

  try:
    # Open connection
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    clientSocket.connect((serverIP, PORT_NUMBER))

    sendThread = threading.Thread(target=clientSendThread, args=(clientSocket,))
    receiveThread = threading.Thread(target=clientReceiveThread, args=(clientSocket,))

    sendThread.start()
    receiveThread.start()

    sendThread.join()
    receiveThread.join()

  except Exception as e:
    print("An error occurred while connecting to the server")
    print(e)

  exit(0)