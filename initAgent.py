import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message
import random
import string
import time
import uuid
import datetime
class initAgent(Agent):

    def __init__(self, jid: str, password: str, args, verify_security: bool = False):
        print("Agent {} created, initializing...".format(jid))
        self.args = args
        super().__init__(jid, password, verify_security)

    async def setup(self):
        print("Agent {} starting...".format(self.name))
        self.add_behaviour(self.SendInitBehviour())
    

    class SendInitBehviour(OneShotBehaviour):
        async def run(self):

            for cnt in range(self.agent.args.fromag, self.agent.args.toag+1):
                tojid = F"agent{cnt}@{self.agent.args.server}"
                msg = Message( to=tojid, sender=self.agent.name)
                msg.set_metadata("performative", "cfp")
                msg.set_metadata("reply_with", str(uuid.uuid4()))   
                msg.body = "Start"

                print("{};{};{};{};{}".format(msg.sender, msg.to, msg.get_metadata("reply_with"), "sent", datetime.datetime.now()))
                await self.send(msg)
