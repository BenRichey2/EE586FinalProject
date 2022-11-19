import sys
import threading
import socket

from capchat_constants import PORT_NUMBER, BUFFER_SIZE, MAX_MESSAGE_LENGTH, ERROR_CODES, END_SEQUENCE

inputPrompt = "> "
senderSeparator = ": "

def clientSendThread(clientSocket:socket.socket, username):
  leave = False
  try:
    while True:
      message = input(inputPrompt)
      # Clear user's input
      print("\033[A\033[J", end="")
      # TODO Find a way to overwrite previous line
      # Ensure message meets certain length criteria
      message = message[0:MAX_MESSAGE_LENGTH]
      if message == "/leave":
        message = "LEAVE " + username + END_SEQUENCE
        leave = True
      else:
        message = "POST " + username + " " + message + END_SEQUENCE
      clientSocket.send(message.encode())
      if leave:
        exit()
  except Exception as e:
    print(e)
    try:
      clientSocket.close()
    except Exception as e:
      print(e)
      return

    return

def clientReceiveThread(clientSocket:socket.socket, username):
  try:
    while True:
      buffer = clientSocket.recv(BUFFER_SIZE).decode()
      messages = buffer.split(END_SEQUENCE)

      for message in messages:
        command = message.split()[0]
        if command == "BROADCAST":
          username = message.split()[1]
          payload = " ".join(message.split()[2:])
          message = username + senderSeparator + payload
          # print("\033[J\033[A")
          print("\033[1i]")
          # print("\033[A\033[999C\n", end="")
          print(message)
          print(inputPrompt, end="")
          sys.stdout.flush()
  except Exception as e:
    print(e)
    try:
      clientSocket.close()
    except Exception as e:
      print(e)
      return

    return

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

    message = "JOIN " + username + END_SEQUENCE
    clientSocket.send(message.encode())

    message = clientSocket.recv(BUFFER_SIZE).decode()
    if message.split()[0] == "ERROR":
      print(ERROR_CODES[message.split()[1]])
      exit(1)
    elif message.split()[0] == "ACCEPT":
      sendThread = threading.Thread(target=clientSendThread, args=(clientSocket,username,))
      receiveThread = threading.Thread(target=clientReceiveThread, args=(clientSocket,username,))

      sendThread.start()
      receiveThread.start()

      sendThread.join()
      receiveThread.join()
    else:
      print("Unknown response received from server. You may be susceptible to an attack.")

  except Exception as e:
    print("An error occurred while connecting to the server")
    print(e)

  exit(0)