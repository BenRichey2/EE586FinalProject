import threading
import socket
import time

from capchat_constants import *

class MessageBoard:
  def __init__(self):
    self.messages = [None for i in range(MESSAGE_HISTORY)]
    self.messagesSender = [None for i in range(MESSAGE_HISTORY)]
    self.messagesServer = [False for i in range(MESSAGE_HISTORY)]
    self.latestMessageIndex = MESSAGE_HISTORY

activeUsernames = []

def serverSendThread(socket:socket.socket, messageBoard:MessageBoard, semaphore:threading.Semaphore, clientUsername):
  try:
    # Update the client on the latest 50 messages received by the message board
    semaphore.acquire() # Synchronize shared access to MessageBoard object

    # Add message indicating user join
    messageBoard.latestMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY
    messageBoard.messagesSender[messageBoard.latestMessageIndex] = SERVER_CODE
    messageBoard.messagesServer[messageBoard.latestMessageIndex] = True
    messageBoard.messages[messageBoard.latestMessageIndex] = clientUsername + " joined"

    # Find the oldest message in case the message history is not full yet
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
      message = ""
      if messageBoard.messagesServer[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] == True:
        message = SERVER_CODE + PROTOCOL_SEPARATOR + messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + END_SEQUENCE
      else:
        message = BROADCAST_CODE + PROTOCOL_SEPARATOR + messageBoard.messagesSender[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + PROTOCOL_SEPARATOR + messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + END_SEQUENCE
      socket.send(message.encode())
      latestSentMessageIndex = (latestSentMessageIndex + 1) % MESSAGE_HISTORY

    semaphore.release()

    while True:
      # Delay to reduce CPU consumption
      time.sleep(DELAY)

      semaphore.acquire() # Synchronize shared access to MessageBoard object

      if clientUsername not in activeUsernames:
        semaphore.release()
        exit()    

      if not latestSentMessageIndex == messageBoard.latestMessageIndex:
        while not latestSentMessageIndex == messageBoard.latestMessageIndex:
          # Send the next mesage that the thread needs
          message = ""
          if messageBoard.messagesServer[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] == True:
            message = SERVER_CODE + PROTOCOL_SEPARATOR + messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + END_SEQUENCE
          else:
            message = BROADCAST_CODE + PROTOCOL_SEPARATOR + messageBoard.messagesSender[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + PROTOCOL_SEPARATOR + messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + END_SEQUENCE
          socket.send(message.encode())
          latestSentMessageIndex = (latestSentMessageIndex + 1) % MESSAGE_HISTORY

      semaphore.release() # Give other threads chance to update MessageBoard

  except Exception as e:
    print("send exception")
    print(e)

    semaphore.acquire()

    try:
      if clientUsername in activeUsernames:
        activeUsernames.remove(clientUsername)

        socket.close()
        
        messageBoard.latestMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY
        messageBoard.messagesSender[messageBoard.latestMessageIndex] = SERVER_CODE
        messageBoard.messagesServer[messageBoard.latestMessageIndex] = True
        messageBoard.messages[messageBoard.latestMessageIndex] = clientUsername + " left"
        
    except Exception as e:
      pass

    semaphore.release()

    return

def serverReceiveThread(socket:socket.socket, messageBoard:MessageBoard, semaphore:threading.Semaphore, clientUsername):
  try:
    while True:

      # Delay to reduce CPU consumption
      time.sleep(DELAY)
      # Receive message
      try:
        buffer = socket.recv(BUFFER_SIZE)

      except TimeoutError:
        buffer = None

      # Check if a timeout occured so that the recv does not block
      if buffer is None:
        continue

      string = buffer.decode()

      messages = string.split(END_SEQUENCE)
      for message in messages:
        if (not message):
          continue

        command = message.split(PROTOCOL_SEPARATOR)[0]
        if command == POST_CODE:
          if (len(message.split(PROTOCOL_SEPARATOR)) < 3):
            print("bad POST received: " + message)
            continue

          username = message.split(PROTOCOL_SEPARATOR)[1]
          payload = PROTOCOL_SEPARATOR.join(message.split(PROTOCOL_SEPARATOR)[2:])

          semaphore.acquire()
          messageBoard.latestMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY
          messageBoard.messagesSender[messageBoard.latestMessageIndex] = username
          messageBoard.messagesServer[messageBoard.latestMessageIndex] = False
          messageBoard.messages[messageBoard.latestMessageIndex] = payload
          semaphore.release()

        elif command == LEAVE_CODE:
          if (len(message.split(PROTOCOL_SEPARATOR)) < 2):
            print("bad LEAVE received: " + message)
            continue

          username = message.split(PROTOCOL_SEPARATOR)[1]
          print(f"recvd leave from {username}")
          
          semaphore.acquire()

          activeUsernames.remove(username)

          # Add message indicating user leave
          messageBoard.latestMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY
          messageBoard.messagesSender[messageBoard.latestMessageIndex] = SERVER_CODE
          messageBoard.messagesServer[messageBoard.latestMessageIndex] = True
          messageBoard.messages[messageBoard.latestMessageIndex] = clientUsername + " left"

          semaphore.release()

          return

  except Exception as e:
    print("receive exception")
    print(e)

    semaphore.acquire()

    try:
      if clientUsername in activeUsernames:
        activeUsernames.remove(clientUsername)

        socket.close()
        
        messageBoard.latestMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY
        messageBoard.messagesSender[messageBoard.latestMessageIndex] = SERVER_CODE
        messageBoard.messagesServer[messageBoard.latestMessageIndex] = True
        messageBoard.messages[messageBoard.latestMessageIndex] = clientUsername + " left"
    except Exception as e:
      pass

    semaphore.release()

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
    message = connectionSocket.recv(BUFFER_SIZE).decode().split(END_SEQUENCE)[0]
    command = message.split(PROTOCOL_SEPARATOR)[0]
    if command == JOIN_CODE:
      if (len(message.split(PROTOCOL_SEPARATOR)) < 2):
        print("bad JOIN received: " + message)
        continue

      clientUsername = message.split(PROTOCOL_SEPARATOR)[1]
      if clientUsername in activeUsernames:
        print("Connection refused: username conflict")

        response = ERROR_CODE + PROTOCOL_SEPARATOR + ERROR_USERNAME_CONFLICT
        connectionSocket.send(response.encode())
        connectionSocket.close()
      else:
        print("Connection received")
        response = ACCEPT_CODE
        connectionSocket.send(response.encode())

        semaphore.acquire()
        activeUsernames.append(clientUsername)
        semaphore.release()
        print(f"Active usernames: {activeUsernames}")

        # Set socket timeout
        connectionSocket.settimeout(SOCK_TIMEOUT)

        sendThread = threading.Thread(target=serverSendThread, args=(connectionSocket,messageBoard,semaphore,clientUsername,))
        receiveThread = threading.Thread(target=serverReceiveThread, args=(connectionSocket,messageBoard,semaphore,clientUsername,))

        sendThread.start()
        receiveThread.start()

        sendThreads.append(sendThread)
        receiveThreads.append(receiveThread)
