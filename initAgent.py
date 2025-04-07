import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message
from tools import *  
import random
import string
import time
import uuid
import datetime


class initAgent(Agent):
        
    async def setup(self):
        print("Agent {} starting...".format(self.name))
        self.add_behaviour(self.SendInitBehviour())
    

    class SendInitBehviour(OneShotBehaviour):
        async def run(self):

            for cnt in range(0, self.agent.get("numagents")):
                tojid = F"agent{cnt}@{self.agent.get('server')}"
                msg = Message( to=tojid, sender=self.agent.name)
                msg.set_metadata("performative", "propose")
                msg.set_metadata("reply_with", str(uuid.uuid4()))   
                msg.body = "Start"

                logMessage(msg, "S")
                await self.send(msg)
