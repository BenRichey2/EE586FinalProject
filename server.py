import threading
import socket

from capchat_constants import PORT_NUMBER, BUFFER_SIZE, MESSAGE_HISTORY, ERROR_CODES

class MessageBoard:
  def __init__(self):
    self.messages = [None for i in range(MESSAGE_HISTORY)]
    self.messagesSender = [None for i in range(MESSAGE_HISTORY)]
    self.latestMessageIndex = MESSAGE_HISTORY
  
activeUsernames = []

def serverSendThread(socket:socket.socket, messageBoard:MessageBoard, semaphore:threading.Semaphore, clientUsername):
  try:
    # Update the client on the latest 50 messages received by the message board
    semaphore.acquire() # Synchronize shared access to MessageBoard object

    # Find the oldest message
    latestSentMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY

    numIterations = 0
    while messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] == None:
      numIterations += 1
      latestSentMessageIndex = (latestSentMessageIndex + 1) % MESSAGE_HISTORY

      if numIterations == MESSAGE_HISTORY:
        latestSentMessageIndex = messageBoard.latestMessageIndex
        break

    # Send all messages from the oldest to the newest to the client

    while not latestSentMessageIndex == messageBoard.latestMessageIndex:
      # Send the next mesage that the thread needs
      message = "BROADCAST " + messageBoard.messagesSender[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + " " + messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY]
      socket.send(message.encode())
      latestSentMessageIndex = (latestSentMessageIndex + 1) % MESSAGE_HISTORY

    semaphore.release()

    while True:
      semaphore.acquire() # Synchronize shared access to MessageBoard object

      if not latestSentMessageIndex == messageBoard.latestMessageIndex:
        while not latestSentMessageIndex == messageBoard.latestMessageIndex:
          # Send the next mesage that the thread needs
          message = "BROADCAST " + messageBoard.messagesSender[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + " " + messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY]
          socket.send(message.encode())
          latestSentMessageIndex = (latestSentMessageIndex + 1) % MESSAGE_HISTORY

      semaphore.release() # Give other threads chance to update MessageBoard
  except Exception as e:
    import ipdb
    ipdb.set_trace()
    print(e)
    if clientUsername in activeUsernames:
      activeUsernames.remove(clientUsername)
    try:
      socket.close()
    except Exception as e:
      pass

    return

def serverReceiveThread(socket:socket.socket, messageBoard:MessageBoard, semaphore:threading.Semaphore, clientUsername):
  try:
    while True:
      #Receive message
      message = socket.recv(BUFFER_SIZE).decode()
      command = message.split()[0]
      if command == "POST":
        username = message.split()[1]
        payload = " ".join(message.split()[2:])
        print(payload)
        semaphore.acquire()
        messageBoard.latestMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY
        messageBoard.messagesSender[messageBoard.latestMessageIndex] = username 
        messageBoard.messages[messageBoard.latestMessageIndex] = payload
        semaphore.release()
      elif command == "LEAVE":
        username = message.split()[1]
        print(f"recvd leave from {username}")
        activeUsernames.remove(username)
        socket.close()
        return

  except Exception as e:
    import ipdb
    ipdb.set_trace()
    print(e)
    if clientUsername in activeUsernames:
      activeUsernames.remove(clientUsername)
    try:
      socket.close()
    except Exception as e:
      pass

    return

if __name__ =="__main__":
  sendThreads = []
  receiveThreads = []

  messageBoard = MessageBoard()

  semaphore = threading.Semaphore()

  serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  serverSocket.bind(('',PORT_NUMBER))

  while True:
    # Try to prevent Python's weird tendency to update old values in a loop
    sendThread = 0
    receiveThread = 0

    # Wait for connection
    serverSocket.listen(1)

    # Accept connection
    connectionSocket, addr = serverSocket.accept()

    # Check username
    message = connectionSocket.recv(BUFFER_SIZE).decode()
    clientUsername = message.split()[1]
    if clientUsername in activeUsernames:
      print("Connection refused: username conflict")

      connectionSocket.send("ERROR 0".encode())
      connectionSocket.close()
    else:
      print("Connection received")
      connectionSocket.send("ACCEPT".encode())

      activeUsernames.append(clientUsername)
      print(f"Active usernames: {activeUsernames}")

      sendThread = threading.Thread(target=serverSendThread, args=(connectionSocket,messageBoard,semaphore,clientUsername,))
      receiveThread = threading.Thread(target=serverReceiveThread, args=(connectionSocket,messageBoard,semaphore,clientUsername,))

      sendThread.start()
      receiveThread.start()

      sendThreads.append(sendThread)
      receiveThreads.append(receiveThread)

  for thread in sendThreads:
    thread.join()

  for thread in receiveThreads:
    thread.join()

  exit(0)