import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message
from spade.template import Template, ANDTemplate
import random
import string
import time
import uuid
import datetime


class queryAgent(Agent):
    async def setup(self):
        
        self.repetitions = self.get("repetitions-num")

        templateInit = Template()
        templateInit.body = "Start"

        templateQuery = Template()
        templateQuery.set_metadata("performative", "query")

        templateInform = Template()
        templateInform.set_metadata("performative", "inform")

        templateComb = ANDTemplate(templateInform, templateQuery)

        self.add_behaviour(self.ReceiveMessage(), templateComb)
        self.add_behaviour(self.ReceiveInit(), templateInit)
    

    class sendMessageBehaviour(OneShotBehaviour):
        async def run(self):
            tojid = "agent{}@{}".format( random.randint(0, self.agent.get("numagents") - 1), self.agent.get("server"))
            msg = Message( to=tojid, sender=self.agent.name)
            msg.set_metadata("performative", "query")
            msg.set_metadata("reply_with", str(uuid.uuid4()))
            
            msg.body = str(''.join(random.choices(string.ascii_letters + string.digits, k=self.agent.get("content-size"))))
#             msg.body = "Hello"

            print("{};{};{};{};{}".format(msg.sender, msg.to, msg.get_metadata("performative"), msg.get_metadata("reply_with"), "sent", datetime.datetime.now()))
            await self.send(msg)

    class ReceiveMessage(CyclicBehaviour):
        async def run(self):
            print("{} Receiving message...".format(self.agent.name))
            msg = await self.receive()  # wait for a message for 300 seconds
            if msg:
                if msg.get_metadata("performative") == "query":
                    rplymsg = msg.make_reply()
                    rplymsg.set_metadata("performative", "inform")        
                    print("{};{};{};{};{}".format(rplymsg.sender, rplymsg.to, rplymsg.get_metadata("performative"), rplymsg.get_metadata("reply_with"), "sent", datetime.datetime.now()))
                    await self.send(rplymsg)

                print("{};{};{};{};{}".format(msg.sender, msg.to, msg.get_metadata("performative"), msg.get_metadata("reply_with"), "received", datetime.datetime.now()))

                
                if self.agent.repetitions > 0:
                    self.agent.repetitions -= 1
                    self.agent.add_behaviour(self.agent.sendMessageBehaviour())

    
    
    class ReceiveInit(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()  # wait for a message for 300 seconds
            if msg:
                print("{};{};{};{};{}".format(msg.sender, msg.to, msg.get_metadata("performative"), msg.get_metadata("reply_with"), "init received", datetime.datetime.now()))
                self.agent.add_behaviour(self.agent.sendMessageBehaviour())
                self.agent.repetitions -= 1
    
