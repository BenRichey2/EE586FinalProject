from capchat_constants import *

class packet:
    def __init__(self, command = None, username = None, payload = None, recv = None):
        # see if it is input from recv or arguments
        if recv is not None:
            # possible values: POST, JOIN, ACCEPT, ERROR, BROADCAST, LEAVE?
            self.command = recv[0:COMMAND_LENGTH]
            self.username = recv[COMMAND_LENGTH:]
        else:
        else:
            self.command = command
        self.username

        #if self.command == "POST":
            
    

    # make packet into string for sending 
    def encode(self):
        return f"{self.command: <{COMMAND_LENGTH}}{self.username: <{UN_LENGTH}{}}"