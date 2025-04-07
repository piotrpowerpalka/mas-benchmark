import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message
from spade.template import Template, ANDTemplate, ORTemplate
from tools import *
import random
import string
import time
import uuid
import datetime


class cfpAgent(Agent):
    async def setup(self):
        
        self.repetitions = self.get("repetitions-num")
        self.groupsize = self.get("groupsize")

        self.agentsSet = []
        for cnt in range(0, self.get("numagents")):
            if cnt != int(self.name.split("@")[0].replace("agent", "")):
                self.agentsSet.append("agent{}@{}".format(cnt, self.get("server")))

        templateInit = Template()
        templateInit.body = "Start"

        templateCFP = Template()
        templateCFP.set_metadata("performative", "cfp")

        templateComb = ORTemplate(templateCFP)

        self.add_behaviour(self.ReceiveMessage(), templateComb)
        self.add_behaviour(self.ReceiveInit(), templateInit)
    

    class sendMessageBehaviour(OneShotBehaviour):
        async def run(self):
            agGrp = tojid = random.choice(self.agent.agentsSet, self.agent.groupsize)   

            for g in agGrp:
                tojid = g
                msg = Message( to=tojid, sender=self.agent.name)
                msg.set_metadata("performative", "CFP")
                msg.set_metadata("reply_with", str(uuid.uuid4()))
                msg.body = str(''.join(random.choices(string.ascii_letters + string.digits, k=self.agent.get("content-size"))))

                logMessage(msg, "S")
                await self.send(msg)

    class ReceiveMessage(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()  # wait for a message for 300 seconds
            if msg:
                logMessage(msg, "R")
                
                if msg.get_metadata("performative") == "CFP":
                    rplymsg = msg.make_reply()
                    rplymsg.set_metadata("performative", "inform")        
                    logMessage(rplymsg, "S")    
                    await self.send(rplymsg)

                
                
                if self.agent.repetitions > 0:
                    self.agent.repetitions -= 1
                    self.agent.add_behaviour(self.agent.sendMessageBehaviour())

    
    
    class ReceiveInit(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()  # wait for a message for 300 seconds
            if msg:
                logMessage(msg, "R")
                self.agent.add_behaviour(self.agent.sendMessageBehaviour())
                self.agent.repetitions -= 1
    
