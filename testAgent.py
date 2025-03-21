from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message
import random
import string
import uuid
import datetime

XMPP_HOST = "serverhello.local"

class testAgent(Agent):

    def __init__(self, jid: str, password: str, verify_security: bool = False):
        print("Agent {} created, initializing...".format(jid))
        super().__init__(jid, password, verify_security)
    
    async def setup(self):
        print("Agent {} starting...".format(self.name))
    
        self.add_behaviour(self.ReceiveOffers())
#        self.add_behaviour(self.sendMessageBehaviour())
    

    class sendMessageBehaviour(OneShotBehaviour):
        async def run(self):
            tojid = F"agent_{random.randint(1,100)}@{XMPP_HOST}"
            msg = Message(to=tojid)
            msg.set_metadata("performative", "inform")
            msg.set_metadata("sender", self.agent.jid)
            msg.set_metadata("reply_with", uuid.uuid4())
            msg.body(''.join(random.choices(string.ascii_letters + string.digits, k=1000)))

            print("{};{};{}".format(msg.get_metadata("reply_with"), "sent", datetime.datetime.now()))
            msg.sent()
            
    class ReceiveOffers(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()  # wait for a message for 300 seconds
            if msg:
                print("{};{};{}".format(msg.get_metadata("reply_with"), "received", datetime.datetime.now()))
