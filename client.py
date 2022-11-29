import sys
import threading
import socket
import tkinter as tk
from PIL import Image, ImageTk

from capchat_constants import *

EXIT = False

# Initialize GUI
# root is the main GUI window object
root = tk.Tk()
# Set the title
root.title("CapChat")
# Set window size
root.geometry("600x520")
# Load in capybara photo
icon = tk.PhotoImage(file=ICON_FILE)
# Add capybara photo as icon
root.wm_iconphoto(True, icon)
# Configure window to send leave message to server when the user hits X
def leave():
  message = LEAVE_CODE + PROTOCOL_SEPARATOR + username + END_SEQUENCE
  clientSocket.send(message.encode())
  EXIT = True
  root.destroy()

root.protocol('WM_DELETE_WINDOW', leave)

# Create the chat box
chat_label = tk.Label(root, text="Chat")
chat_label.pack(side=tk.TOP)
chat = tk.Text(root, height=25, width=65, state="disabled")
chat.pack()
# Add input text box
input_label = tk.Label(root, text="Enter Message Below")
input_label.pack(side=tk.TOP, pady=(5,0))
input_box = tk.Text(root, height=3, width=60)
input_box.pack(side=tk.LEFT, padx=(15,0))

def sendMessage():
  try:
    # Get message from input box
    message = input_box.get(1.0, "end-1c")
    # Clear entry
    input_box.delete(1.0, tk.END)
    message = message.replace(END_SEQUENCE, "")
    message = message[0:MAX_MESSAGE_LENGTH]
    message = POST_CODE + PROTOCOL_SEPARATOR + username + PROTOCOL_SEPARATOR + message + END_SEQUENCE
    clientSocket.send(message.encode())
  except Exception as e:
    print(e)
    try:
      clientSocket.close()
    except Exception as e:
      print(e)
      return

    return

  return

def clientReceiveThread(clientSocket:socket.socket, username):
  try:
    while True:
      buffer = clientSocket.recv(BUFFER_SIZE)

      # catch socket close after /leave
      if not buffer or EXIT:
        exit()

      string = buffer.decode()

      messages = string.split(END_SEQUENCE)
      for message in messages:
        if (not message):
          continue

        command = message.split(PROTOCOL_SEPARATOR)[0]
        if command == BROADCAST_CODE:
          if (len(message.split(PROTOCOL_SEPARATOR)) < 3):
            print("bad BROADCAST received: " + message)
            continue
          username = message.split(PROTOCOL_SEPARATOR)[1]
          payload = PROTOCOL_SEPARATOR.join(message.split(PROTOCOL_SEPARATOR)[2:])

          newlineSpacing = len(username) + len(SENDER_SEPARATOR)
          newlineReplace = "\n"
          for i in range(0, newlineSpacing):
            newlineReplace += " "
          payload = payload.replace("\n", newlineReplace)

          output = username + SENDER_SEPARATOR + payload + "\n"
          # Update Chat box to show new message
          # First enable box to be edited
          chat.configure(state="normal")
          # Then insert new message
          chat.insert(tk.END, output)
          # Auto scroll to the bottom of the chat to show the most recent
          # message
          chat.see(tk.END)
          # Finally, disable box from editing
          chat.configure(state="disabled")
        elif command == SERVER_CODE:
          if (len(message.split(PROTOCOL_SEPARATOR)) < 2):
            print("bad SERVER received: " + message)
            continue
          payload = PROTOCOL_SEPARATOR.join(message.split(PROTOCOL_SEPARATOR)[1:])
          output = payload + "\n"
          # Update Chat box to show new message
          # First enable box to be edited
          chat.configure(state="normal")
          # Then insert new message
          chat.insert(tk.END, output)
          # Auto scroll to the bottom of the chat to show the most recent
          # message
          chat.see(tk.END)
          # Finally, disable box from editing
          chat.configure(state="disabled")
  except Exception as e:
    print(e)
    try:
      clientSocket.close()
    except Exception as e:
      print(e)
      return

    return

if __name__ =="__main__":
  if len(sys.argv) < 3:
    print("Usage: python3 client.py <server ip address> <username>")
    exit(1)

  serverIP = sys.argv[1]
  username = " ".join(sys.argv[2:])

  try:
    # Open connection
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    clientSocket.connect((serverIP, PORT_NUMBER))

    message = JOIN_CODE + PROTOCOL_SEPARATOR + username + END_SEQUENCE
    clientSocket.send(message.encode())

    message = clientSocket.recv(BUFFER_SIZE).decode()
    if message.split(PROTOCOL_SEPARATOR)[0] == ERROR_CODE:
      print(ERROR_CODES[message.split(PROTOCOL_SEPARATOR)[1]])
      exit(1)
    elif message.split(PROTOCOL_SEPARATOR)[0] == ACCEPT_CODE:
      # Load in send message icon
      send_img = Image.open(SEND_ICON_FILE)
      send_img = send_img.resize((30,30), Image.ANTIALIAS)
      send_icon = ImageTk.PhotoImage(send_img)
      # Create send message button
      send_button = tk.Button(root, image=send_icon, command=sendMessage)
      send_button.pack(side=tk.RIGHT, padx=(0,25))
      receiveThread = threading.Thread(target=clientReceiveThread, args=(clientSocket,username,))

      receiveThread.start()

      # Start up the GUI
      # TODO Figure out how to make the GUI send a /leave command when the user
      # hits the X button to quit the GUI window
      root.mainloop()

      receiveThread.join()
    else:
      print("Unknown response received from server. You may be susceptible to an attack.")

  except KeyboardInterrupt as err:
    print("Ctrl-c caught. Notifying threads to exit.")
    EXIT = True
    root.destroy()

  except Exception as e:
    print("An error occurred while connecting to the server")
    print(e)

  exit(0)