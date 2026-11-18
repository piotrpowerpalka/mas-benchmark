from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour, PeriodicBehaviour
from spade.message import Message
from spade.template import Template, ANDTemplate, ORTemplate
from tools import *
import random
import string
import time
import uuid
import datetime


class queryAgent(Agent):
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

        templateQuery = Template()
        templateQuery.set_metadata("performative", "query")

        templateInform = Template()
        templateInform.set_metadata("performative", "inform")

        templateComb = ORTemplate(templateInform, templateQuery)

        self.add_behaviour(self.ReceiveMessage(), templateComb)
        self.add_behaviour(self.ReceiveInit(), templateInit)
    

    class sendMessageBehaviour(OneShotBehaviour):
        async def run(self):
            tojid = random.choice(self.agent.agentsSet)
            msg = Message( to=tojid, sender=self.agent.name)
            msg.set_metadata("performative", "query")
            msg.set_metadata("reply_with", "rw-" + str(uuid.uuid4()))
            msg.set_metadata("conversation_id", "cid-" + str(uuid.uuid4()))
            
            msg.body = str(''.join(random.choices(string.ascii_letters + string.digits, k=self.agent.get("content-size"))))

            logMessage(msg, "S")
            await self.send(msg)

    class ReceiveMessage(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()  # wait for a message for 300 seconds
            if msg:
                logMessage(msg, "R")

                if msg.get_metadata("performative") == "query":
                    rplymsg = msg.make_reply()
                    rplymsg.set_metadata("performative", "inform")        
                    rplymsg.set_metadata("reply_with", "rw-" + str(uuid.uuid4()))
                    rplymsg.body = str(''.join(random.choices(string.ascii_letters + string.digits, k=self.agent.get("content-size"))))
                    
                    logMessage(rplymsg, "S")    
                    await self.send(rplymsg)
    
    
    class ReceiveInit(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()  # wait for a message for 300 seconds
            if msg:
                logMessage(msg, "R")
                self.agent.add_behaviour(self.agent.SendTickerBehaviour(period=self.agent.period))

    class SendTickerBehaviour(PeriodicBehaviour):
        async def run(self):
            if self.agent.repetitions <= 0:
                self.kill()
                return

            self.agent.repetitions -= 1
            self.agent.add_behaviour(self.agent.sendMessageBehaviour())

            if self.agent.repetitions <= 0:
                self.kill()
    
