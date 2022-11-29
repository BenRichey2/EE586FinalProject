import threading
import socket

from capchat_constants import *

class MessageBoard:
  def __init__(self):
    self.messages = [None for i in range(MESSAGE_HISTORY)]
    self.messagesSender = [None for i in range(MESSAGE_HISTORY)]
    self.latestMessageIndex = MESSAGE_HISTORY

EXIT = False

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

    # Add message indicating user join
    messageBoard.latestMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY
    messageBoard.messagesSender[messageBoard.latestMessageIndex] = SERVER_CODE
    messageBoard.messages[messageBoard.latestMessageIndex] = clientUsername + " joined"

    # Send all messages from the oldest to the newest to the client

    while not latestSentMessageIndex == messageBoard.latestMessageIndex:
      # Send the next mesage that the thread needs
      message = ""
      if messageBoard.messagesSender[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] == SERVER_CODE:
        message = SERVER_CODE + PROTOCOL_SEPARATOR + messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + END_SEQUENCE
      else:
        message = BROADCAST_CODE + PROTOCOL_SEPARATOR + messageBoard.messagesSender[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + PROTOCOL_SEPARATOR + messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + END_SEQUENCE
      socket.send(message.encode())
      latestSentMessageIndex = (latestSentMessageIndex + 1) % MESSAGE_HISTORY

    semaphore.release()

    while True:
      if clientUsername not in activeUsernames or EXIT:
        exit()

      semaphore.acquire() # Synchronize shared access to MessageBoard object

      if not latestSentMessageIndex == messageBoard.latestMessageIndex:
        while not latestSentMessageIndex == messageBoard.latestMessageIndex:
          # Send the next mesage that the thread needs
          message = ""
          if messageBoard.messagesSender[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] == SERVER_CODE:
            message = SERVER_CODE + PROTOCOL_SEPARATOR + messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + END_SEQUENCE
          else:
            message = BROADCAST_CODE + PROTOCOL_SEPARATOR + messageBoard.messagesSender[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + PROTOCOL_SEPARATOR + messageBoard.messages[(latestSentMessageIndex + 1) % MESSAGE_HISTORY] + END_SEQUENCE
          socket.send(message.encode())
          latestSentMessageIndex = (latestSentMessageIndex + 1) % MESSAGE_HISTORY

      semaphore.release() # Give other threads chance to update MessageBoard

  except Exception as e:
    print("send exception")
    # import ipdb
    # ipdb.set_trace()
    print(e)

    try:
      if clientUsername in activeUsernames:
        activeUsernames.remove(clientUsername)

        socket.close()

        # Add message indicating user leave
        semaphore.acquire()
        messageBoard.latestMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY
        messageBoard.messagesSender[messageBoard.latestMessageIndex] = SERVER_CODE
        messageBoard.messages[messageBoard.latestMessageIndex] = clientUsername + " left"
        semaphore.release()
    except Exception as e:
      pass

    return

def serverReceiveThread(socket:socket.socket, messageBoard:MessageBoard, semaphore:threading.Semaphore, clientUsername):
  try:
    while True:
      if EXIT:
        exit()

      #Receive message
      buffer = socket.recv(BUFFER_SIZE)
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
          messageBoard.messages[messageBoard.latestMessageIndex] = payload
          semaphore.release()

        elif command == LEAVE_CODE:
          if (len(message.split(PROTOCOL_SEPARATOR)) < 2):
            print("bad LEAVE received: " + message)
            continue

          username = message.split(PROTOCOL_SEPARATOR)[1]
          print(f"recvd leave from {username}")
          activeUsernames.remove(username)
          socket.close()

          # Add message indicating user leave
          semaphore.acquire()
          messageBoard.latestMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY
          messageBoard.messagesSender[messageBoard.latestMessageIndex] = SERVER_CODE
          messageBoard.messages[messageBoard.latestMessageIndex] = clientUsername + " left"
          semaphore.release()

          return

  except Exception as e:
    # import ipdb
    # ipdb.set_trace()
    print("receive exception")
    print(e)

    try:
      if clientUsername in activeUsernames:
        activeUsernames.remove(clientUsername)

        socket.close()

        # Add message indicating user leave
        semaphore.acquire()
        messageBoard.latestMessageIndex = (messageBoard.latestMessageIndex + 1) % MESSAGE_HISTORY
        messageBoard.messagesSender[messageBoard.latestMessageIndex] = SERVER_CODE
        messageBoard.messages[messageBoard.latestMessageIndex] = clientUsername + " left"
        semaphore.release()
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

  try:
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

          activeUsernames.append(clientUsername)
          print(f"Active usernames: {activeUsernames}")

          sendThread = threading.Thread(target=serverSendThread, args=(connectionSocket,messageBoard,semaphore,clientUsername,))
          receiveThread = threading.Thread(target=serverReceiveThread, args=(connectionSocket,messageBoard,semaphore,clientUsername,))

          sendThread.start()
          receiveThread.start()

          sendThreads.append(sendThread)
          receiveThreads.append(receiveThread)

  except KeyboardInterrupt as err:
    print("Ctrl-c caught. Notifying send/receive threads to quit.")
    EXIT = True

    for thread in sendThreads:
      thread.join()

    for thread in receiveThreads:
      thread.join()

    exit(0)