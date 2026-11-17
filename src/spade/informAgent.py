import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message
from spade.template import Template 
from tools import *

import random
import string
import time
import uuid
import datetime


class informAgent(Agent):
    async def setup(self):
        random.seed(self.get("seed"))

        self.repetitions = self.get("repetitions-num")

        self.agentsSet = []
        for cnt in range(0, self.get("numagents")):
            if cnt != int(self.name.split("@")[0].replace("agent", "")):
                self.agentsSet.append("agent{}@{}".format(cnt, self.get("server")))
        
        templateInit = Template()
        templateInit.body = "Start"

        templateInform = Template()
        templateInform.set_metadata("performative", "inform")

        self.add_behaviour(self.ReceiveOffers(), templateInform)
        self.add_behaviour(self.ReceiveInit(), templateInit)

        
    class sendMessageBehaviour(OneShotBehaviour):
        async def run(self):
            
            tojid = random.choice(self.agent.agentsSet)
            msg = Message( to=tojid, sender=self.agent.name)
            msg.set_metadata("performative", "inform")
            msg.set_metadata("reply_with", "rw-" + str(uuid.uuid4()))
            msg.set_metadata("conversation_id", "cid-" + str(uuid.uuid4()))

            msg.body = str(''.join(random.choices(string.ascii_letters + string.digits, k=self.agent.get("content-size"))))
            
            logMessage(msg, "S")

            await self.send(msg)

    class ReceiveOffers(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(15)  # wait for a message for 15 seconds
            if msg:
                logMessage(msg, "R")
                
                if self.agent.repetitions > 0:
                    self.agent.repetitions -= 1
                    await asyncio.sleep(100 / 1000)
                    self.agent.add_behaviour(self.agent.sendMessageBehaviour())
           
                elif self.agent.repetitions == 0:
                    pass
#                    logInfoMessage("Stoping agent", self.agent.name)
#                    await self.agent.stop()
    
    class ReceiveInit(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(30)  # wait for a message for 300 seconds
            if msg:
                logMessage(msg, "R")
                self.agent.add_behaviour(self.agent.sendMessageBehaviour())
                self.agent.repetitions -= 1
#            else:
#               logInfoMessage("No init message received - something is wrong", self.agent.name)
    
