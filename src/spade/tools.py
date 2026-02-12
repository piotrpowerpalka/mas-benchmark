from spade.message import Message
import datetime
import string

def logMessage(msg: Message, str: string):
    sender = str(msg.sender).split("@")[0]  # Extract the part before the first "/"
    to = str(msg.to).split("@")[0]  # Extract the part before the first "/"
    print("{};{};{};{};{};{};{}".format(sender, to, msg.get_metadata("performative"), msg.get_metadata("reply_with"), msg.get_metadata("conversation_id"), str, datetime.datetime.now()))
                
    
def logInitMessage(str: string, agentname: string):
    print("init;{};{};{}".format(str, agentname, datetime.datetime.now()))

def logInfoMessage(str: string, agentname: string):
    print("info;{};{};{}".format(str, agentname, datetime.datetime.now()))