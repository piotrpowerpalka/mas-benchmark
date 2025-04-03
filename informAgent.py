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


class informAgent(generalAgent):
    async def setup(self):
        
        self.repetitions = self.get("repetitions-num")

        templateInit = Template()
        templateInit.body = "Start"

        templateInform = Template()
        templateInform.set_metadata("performative", "inform")

        self.add_behaviour(self.ReceiveOffers(), templateInform)
        self.add_behaviour(self.ReceiveInit(), templateInit)
    

    class sendMessageBehaviour(OneShotBehaviour):
        async def run(self):
            tojid = "agent{}@{}".format( random.randint(0, self.agent.get("numagents") - 1), self.agent.get("server"))
            msg = Message( to=tojid, sender=self.agent.name)
            msg.set_metadata("performative", "inform")
            msg.set_metadata("reply_with", str(uuid.uuid4()))
            
            msg.body = str(''.join(random.choices(string.ascii_letters + string.digits, k=self.agent.get("content-size"))))
#             msg.body = "Hello"

            print("{};{};{};{};{}".format(msg.sender, msg.to, msg.get_metadata("performative"), msg.get_metadata("reply_with"), "sent", datetime.datetime.now()))
            await self.send(msg)

    class ReceiveOffers(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()  # wait for a message for 300 seconds
            if msg:
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
    
