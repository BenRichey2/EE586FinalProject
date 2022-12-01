PORT_NUMBER = 10000
BUFFER_SIZE = 2048
MESSAGE_HISTORY = 50
MAX_MESSAGE_LENGTH = 1000

ERROR_USERNAME_CONFLICT = "0"

ERROR_CODES = {
  "0": "Username already taken"
}

JOIN_CODE = "JOIN"
LEAVE_CODE = "LEAVE"
POST_CODE = "POST"
BROADCAST_CODE = "BCST"
SERVER_CODE = "SRVR"
ACCEPT_CODE = "ACCEPT"
ERROR_CODE = "ERROR"

PROTOCOL_SEPARATOR = "\0"
SENDER_SEPARATOR = "> "
END_SEQUENCE = "\0\0"

ICON_FILE = "./images/capybara.png"
SEND_ICON_FILE = "./images/send_icon.png"

DELAY = 0.001 # Add 1ms delay to server send and recv threads
SOCK_TIMEOUT = 0.25 # Only let socket operations block for a quarter of a second
