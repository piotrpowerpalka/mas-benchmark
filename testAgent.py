import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message
from spade.template import Template 
import random
import string
import time
import uuid
import datetime


class testAgent(Agent):
    
    def __init__(self, jid: str, password: str, args, verify_security: bool = False):
        print("Agent {} created, initializing...".format(jid))
        self.args = args
        super().__init__(jid, password, verify_security)
    
    async def setup(self):
        print("Agent {} starting...".format(self.name))
        templateInit = Template()
        templateInit.set_metadata("performative", "cfp")

        templateOffer = Template()
        templateOffer.set_metadata("performative", "inform")

        self.add_behaviour(self.ReceiveOffers(), templateOffer)
        self.add_behaviour(self.ReceiveInit(), templateInit)
    

    class sendMessageBehaviour(OneShotBehaviour):
        async def run(self):
            tojid = F"agent{random.randint(0, self.agent.args.numagents - 1)}@{self.agent.args.server}"
            msg = Message( to=tojid, sender=self.agent.name)
            msg.set_metadata("performative", "inform")
            msg.set_metadata("reply_with", str(uuid.uuid4()))
#            msg.body(''.join(random.choices(string.ascii_letters + string.digits, k=1000)))
            msg.body = "Hello"

            print("{};{};{};{};{}".format(msg.sender, msg.to, msg.get_metadata("reply_with"), "sent", datetime.datetime.now()))
            await self.send(msg)

    class ReceiveInit(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()  # wait for a message for 300 seconds
            if msg:
                print("{};{};{};{};{}".format(msg.sender, msg.to, msg.get_metadata("reply_with"), "init received", datetime.datetime.now()))
                self.agent.add_behaviour(self.agent.sendMessageBehaviour())
            
    
    class ReceiveOffers(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()  # wait for a message for 300 seconds
            if msg:
                print("{};{};{};{};{}".format(msg.sender, msg.to, msg.get_metadata("reply_with"), "received", datetime.datetime.now()))
