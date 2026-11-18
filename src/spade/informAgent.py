from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour, PeriodicBehaviour
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
        self.period = self.get("period") / 1000

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
    
    class ReceiveInit(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(30)  # wait for a message for 300 seconds
            if msg:
                logMessage(msg, "R")
                self.agent.add_behaviour(self.agent.SendTickerBehaviour(period=self.agent.period))
#            else:
#               logInfoMessage("No init message received - something is wrong", self.agent.name)

    class SendTickerBehaviour(PeriodicBehaviour):
        async def run(self):
            if self.agent.repetitions <= 0:
                self.kill()
                return

            self.agent.repetitions -= 1
            self.agent.add_behaviour(self.agent.sendMessageBehaviour())

            if self.agent.repetitions <= 0:
                self.kill()
    
