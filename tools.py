from spade.message import Message
import datetime
import string

def logMessage(msg: Message, str: string):
    print("{};{};{};{};{}".format(msg.sender, msg.to, msg.get_metadata("performative"), msg.get_metadata("reply_with"), str, datetime.datetime.now()))
                
    
    
