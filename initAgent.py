import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message
import random
import string
import time
import uuid
import datetime

XMPP_HOST = "serverhello"

class initAgent(Agent):

    
    async def setup(self):
        print("Agent {} starting...".format(self.name))
        self.add_behaviour(self.SendInitBehviour())
    

    class SendInitBehviour(OneShotBehaviour):
        async def run(self):

            for cnt in range(0,10):
                tojid = F"agent{cnt}@{XMPP_HOST}"
                msg = Message( to=tojid, sender=self.agent.name)
                msg.set_metadata("performative", "cfp")
                msg.set_metadata("reply_with", str(uuid.uuid4()))   
                msg.body = "Start"

                print("{};{};{};{};{}".format(msg.sender, msg.to, msg.get_metadata("reply_with"), "sent", datetime.datetime.now()))
                await self.send(msg)
