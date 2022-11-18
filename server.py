import threading
import socket

from capchat_constants import PORT_NUMBER, BUFFER_SIZE, MESSAGE_HISTORY


class MessageBoard:
  def __init__(self):
    self.messages = [None for i in range(MESSAGE_HISTORY)]
    self.latestMessageIndex = MESSAGE_HISTORY
    self.activeUsernames = [] # TODO: don't allow multiple users with same name


def serverSendThread(socket:socket.socket, messageBoard:MessageBoard, semaphore:threading.Semaphore):
  print("send thread created")

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

  print(latestSentMessageIndex)

  # Send all messages from the oldest to the newest to the client

  while not latestSentMessageIndex == messageBoard.latestMessageIndex:
    # Send the next mesage that the thread needs
    socket.send(messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY].encode())
    latestSentMessageIndex = (latestSentMessageIndex + 1) % MESSAGE_HISTORY

  semaphore.release()

  print("caught up")

  while True:
    semaphore.acquire() # Synchronize shared access to MessageBoard object

    if not latestSentMessageIndex == messageBoard.latestMessageIndex:
      while not latestSentMessageIndex == messageBoard.latestMessageIndex:
        # Send the next mesage that the thread needs
        socket.send(messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY].encode())
        latestSentMessageIndex = (latestSentMessageIndex + 1) % MESSAGE_HISTORY

    semaphore.release() # Give other threads chance to update MessageBoard


def serverReceiveThread(socket:socket.socket, messageBoard:MessageBoard, semaphore:threading.Semaphore):
  print("receive thread created")

  while True:
    #Receive message
    message = socket.recv(BUFFER_SIZE).decode()
    print(message)
    semaphore.acquire()
    messageBoard.latestMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY
    messageBoard.messages[messageBoard.latestMessageIndex] = message
    semaphore.release()


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

    print("Connection received")

    sendThread = threading.Thread(target=serverSendThread, args=(connectionSocket,messageBoard,semaphore,))
    receiveThread = threading.Thread(target=serverReceiveThread, args=(connectionSocket,messageBoard,semaphore,))

    sendThread.start()
    receiveThread.start()

    sendThreads.append(sendThread)
    receiveThreads.append(receiveThread)

  for thread in sendThreads:
    thread.join()

  for thread in receiveThreads:
    thread.join()

  exit(0)