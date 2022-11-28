import sys
import threading
import socket
import tkinter as tk

from capchat_constants import PORT_NUMBER, BUFFER_SIZE, MAX_MESSAGE_LENGTH, ERROR_CODES, END_SEQUENCE, ICON_FILE

inputPrompt = "> "
senderSeparator = ": "

# Initialize GUI
# root is the main GUI window object
root = tk.Tk()
# Set the title
root.title("CapChat")
# Load in capybara photo
icon = tk.PhotoImage(file=ICON_FILE)
# Add capybara photo as icon
root.wm_iconphoto(True, icon)
# Create the chat box
chat = tk.Text(root, height=30, width=40)
# Add the chat to the window
chat.pack()

#TODO Add input box so the user can send and receive messages all in the GUI

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
          message = username + senderSeparator + payload + "\n"
          # Update Chat box to show new message
          chat.insert(tk.END, message)
          # Auto scroll to the bottom of the chat to show the most recent
          # message
          chat.see(tk.END)
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

      # Start up the GUI
      # TODO Figure out how to make the GUI send a /leave command when the user
      # hits the X button to quit the GUI window
      root.mainloop()

      sendThread.join()
      receiveThread.join()
    else:
      print("Unknown response received from server. You may be susceptible to an attack.")

  except Exception as e:
    print("An error occurred while connecting to the server")
    print(e)

  exit(0)