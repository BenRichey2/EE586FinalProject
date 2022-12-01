import sys
import threading
import socket
import tkinter as tk
from PIL import Image, ImageTk

from capchat_constants import *

WINDOW_WIDTH = 600
WINDOW_HEIGHT = 520

OUTPUT_WIDTH = 65
OUTPUT_HEIGHT = 25

# Initialize GUI
# root is the main GUI window object
root = tk.Tk()
# Set the title
root.title("CapChat")
# Set window size
root.geometry(str(WINDOW_WIDTH)+"x"+str(WINDOW_HEIGHT))
root.configure(bg=WINDOW_BG_COLOR)
# Load in capybara photo
icon = tk.PhotoImage(file=ICON_FILE)
# Add capybara photo as icon
root.wm_iconphoto(True, icon)
# Configure window to send leave message to server when the user hits X
def leave():
  try:
    message = LEAVE_CODE + PROTOCOL_SEPARATOR + username + END_SEQUENCE
    clientSocket.send(message.encode())
    clientSocket.close()
  except:
    pass
  root.destroy()

root.protocol('WM_DELETE_WINDOW', leave)

# Create the chat box
chat_label = tk.Label(root, text="Chat", bg=LABEL_COLOR, font=FONT)
chat_label.pack(side=tk.TOP)
chat = tk.Text(root, height=OUTPUT_HEIGHT, width=OUTPUT_WIDTH, state="disabled",
                bg=TEXT_BOX_BG_COLOR, fg=TEXT_COLOR, bd=0)
chat.pack()
# Add input text box
input_label = tk.Label(root, text="Enter Message Below", bg=LABEL_COLOR, font=FONT)
input_label.pack(side=tk.TOP, pady=(5,0))
input_box = tk.Text(root, height=3, width=60, bg=INPUT_BOX_BG_COLOR)
input_box.pack(side=tk.LEFT, padx=(15,0))

def sendMessage():
  try:
    # Get message from input box
    message = input_box.get(1.0, "end-1c")

    if not message:
      return

    # Clear entry
    input_box.delete(1.0, tk.END)
    message = message.replace(END_SEQUENCE, "")
    message = message[0:MAX_MESSAGE_LENGTH]
    message = POST_CODE + PROTOCOL_SEPARATOR + username + PROTOCOL_SEPARATOR + message + END_SEQUENCE
    clientSocket.send(message.encode())
  except Exception as e:
    print("send exception")
    print(e)
    try:
      clientSocket.close()
    except Exception as e:
      print(e)

  return

def clientReceiveThread(clientSocket:socket.socket, username):
  try:
    while True:
      try:
        buffer = clientSocket.recv(BUFFER_SIZE)

      except TimeoutError as err:
        buffer = None

      # The client didn't recv anything within the timeout, but that doesn't
      # necessarily mean they left
      if buffer is None:
        continue

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

          # Create proper spacing for newlines and overflow lines

          # Compute how much padding must be added and prepare the string with the padding
          newlineSpacing = len(username) + len(SENDER_SEPARATOR)
          newlineReplace = "\n"
          for i in range(0, newlineSpacing):
            newlineReplace += " "

          # Go through each line of the payload and add an artificial break if the line overflows
          payloadLines = payload.split("\n")
          payloadLinesNoOverflow = []
          for line in payloadLines:
            splitNumber = 0
            while len(line[(OUTPUT_WIDTH - newlineSpacing) * splitNumber:]) > OUTPUT_WIDTH - newlineSpacing:
              payloadLinesNoOverflow.append(line[(OUTPUT_WIDTH - newlineSpacing) * splitNumber:(OUTPUT_WIDTH - newlineSpacing) * (splitNumber + 1)])
              splitNumber += 1
            payloadLinesNoOverflow.append(line[(OUTPUT_WIDTH - newlineSpacing) * splitNumber:])

          # Rebuild the payload with the padding at the start of each line
          reconstructedPayload = newlineReplace.join(payloadLinesNoOverflow[:])

          output = username + SENDER_SEPARATOR + reconstructedPayload + "\n"
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

  except OSError:
    # The socket was closed because the user quit the window
    exit()

  except Exception as e:
    print("receive exception")
    print(e)
    try:
      clientSocket.close()
    except Exception as e:
      print(e)

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

    message = clientSocket.recv(BUFFER_SIZE).decode().split(END_SEQUENCE)[0]
    command = message.split(PROTOCOL_SEPARATOR)[0]
    if command == ERROR_CODE:
      if (len(message.split(PROTOCOL_SEPARATOR)) < 2):
        print("bad ERROR received: " + message)
        exit(1)
      print(ERROR_CODES[message.split(PROTOCOL_SEPARATOR)[1]])
      exit(1)
    elif command == ACCEPT_CODE:
      if (len(message.split(PROTOCOL_SEPARATOR)) < 1):
        print("bad ACCEPT received: " + message)
        exit(1)

      # Load in send message icon
      send_img = Image.open(SEND_ICON_FILE)
      send_img = send_img.resize((30,30), Image.Resampling.LANCZOS)
      send_icon = ImageTk.PhotoImage(send_img)
      # Create send message button
      send_button = tk.Button(root, image=send_icon, command=sendMessage, bg=SEND_BUTTON_COLOR)
      send_button.pack(side=tk.RIGHT, padx=(0,25))
      # Set socket timeout so we don't block on recv
      clientSocket.settimeout(SOCK_TIMEOUT)
      receiveThread = threading.Thread(target=clientReceiveThread, args=(clientSocket,username,))

      receiveThread.start()

      # Start up the GUI
      root.mainloop()
    else:
      print("Unknown response received from server. You may be susceptible to an attack.")

  except Exception as e:
    print("An error occurred while connecting to the server")
    print(e)

  exit(0)