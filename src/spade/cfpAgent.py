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

        random.seed(self.get("seed"))
        
        self.offers = []  # List to store offers
        self.refusals = []  # List to store refusals

        self.repetitions = self.get("repetitions-num")
        self.groupsize = self.get("groupsize")

        self.agentsSet = []
        for cnt in range(0, self.get("numagents")):
            if cnt != int(self.name.split("@")[0].replace("agent", "")):
                self.agentsSet.append("agent{}@{}".format(cnt, self.get("server")))

        templateInit = Template()
        templateInit.body = "Start"

        templateCFP = Template()
        templateCFP.set_metadata("performative", "CFP")

        templatePropose = Template()
        templatePropose.set_metadata("performative", "propose")
        
        templateRefuse = Template()
        templateRefuse.set_metadata("performative", "refuse")

        templateAccept = Template()
        templateAccept.set_metadata("performative", "accept-proposal")

        templateReject = Template()
        templateReject.set_metadata("performative", "reject-proposal")

        templateCombMess = ORTemplate(templateCFP, ORTemplate(templateAccept, templateReject))
        templateCombOffers = ORTemplate(templatePropose, templateRefuse)

        self.add_behaviour(self.ReceiveMessage(), templateCombMess)
        self.add_behaviour(self.ReceiveOffers(), templateCombOffers)
        self.add_behaviour(self.ReceiveInit(), templateInit)
        
    class ReceiveOffers(CyclicBehaviour):
        async def run(self):
            msg = await self.receive() 
            if msg:     
                logMessage(msg, "R")
                
                if msg.get_metadata("performative") == "propose":
                    self.agent.offers.append(msg)  # store the offers in a list

                if msg.get_metadata("performative") == "refuse":
                    self.agent.refusals.append(msg)

                # end of collecting offers and refusals
                if len(self.agent.offers) + len(self.agent.refusals) == self.agent.groupsize:
                    winOffer = random.choice(self.agent.offers)  # Randomly select one offer
                    self.agent.offers.remove(winOffer)  # Remove the winning offer from the list

                    rplymsg = winOffer.make_reply()
                    rplymsg.set_metadata("performative", "accept-proposal")
                    rplymsg.set_metadata("reply_with", "rw-" + str(uuid.uuid4()))
                    rplymsg.body = str(''.join(random.choices(string.ascii_letters + string.digits, k=self.agent.get("content-size"))))
                    logMessage(rplymsg, "S")
                    await self.send(rplymsg)

                    for offer in self.agent.offers:
                            rplymsg = offer.make_reply()
                            rplymsg.set_metadata("performative", "reject-proposal")      
                            rplymsg.set_metadata("reply_with", "rw-" + str(uuid.uuid4()))  
                            rplymsg.body = str(''.join(random.choices(string.ascii_letters + string.digits, k=self.agent.get("content-size"))))
                            logMessage(rplymsg, "S")    
                            await self.send(rplymsg) 

                    # begin a new round of CFP
                    if self.agent.repetitions > 0:
                        self.agent.repetitions -= 1
                        self.agent.add_behaviour(self.agent.sendMessageBehaviour())
            
                    elif self.agent.repetitions == 0:
                        logInfoMessage("Stoping agent", self.agent.name)
                        await self.agent.stop()


    class sendMessageBehaviour(OneShotBehaviour):
        async def run(self):
            agGrp = random.sample(self.agent.agentsSet, self.agent.groupsize)   
            self.agent.offers.clear()
            self.agent.refusals.clear()

            for g in agGrp:
                tojid = g
                msg = Message(to=tojid, sender=self.agent.name)
                msg.set_metadata("performative", "CFP")
                msg.set_metadata("reply_with", "rw-" + str(uuid.uuid4()))
                msg.set_metadata("conversation_id", "cid-" + str(uuid.uuid4()))
                msg.body = str(''.join(random.choices(string.ascii_letters + string.digits, k=self.agent.get("content-size"))))
                logMessage(msg, "S")
                await self.send(msg)

    class ReceiveMessage(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()  
            if msg:
                logMessage(msg, "R")
                
                if msg.get_metadata("performative") == "CFP":
                    rplymsg = msg.make_reply()
                    if random.random() <= 0.9:  # Randomly decide to accept or refuse
                        rplymsg.set_metadata("performative", "propose")
                    else:
                        rplymsg.set_metadata("performative", "refuse")

                    rplymsg.set_metadata("reply_with", "rw-" + str(uuid.uuid4()))
                    rplymsg.body = str(''.join(random.choices(string.ascii_letters + string.digits, k=self.agent.get("content-size"))))
                    logMessage(rplymsg, "S")    
                    await self.send(rplymsg)
    
    
    class ReceiveInit(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()  
            if msg:
                logMessage(msg, "R")
                self.agent.add_behaviour(self.agent.sendMessageBehaviour())
                self.agent.repetitions -= 1
    
