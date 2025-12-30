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
#-        b = self.SendInitBehviour()
#-        self.add_behaviour(b)
        self.server = self.get("server")
        self.numagents = int(self.get("numagents"))
        self.all_agents = [f"agent{cnt}@{self.server}" for cnt in range(0, self.numagents)]

        self.ready = set()
        self.acked = set()
        self.start_sent = False

        # Tunables (kept minimal and hardcoded)
        self.ready_timeout_s = 30       # wait up to 30s for READY barrier
        self.retx_interval_s = 5        # retransmit START every 5s
        self.max_retx_rounds = 3        # up to 3 retransmit rounds

        self.ready_deadline = time.time() + self.ready_timeout_s
        self.next_retx_ts = None
        self.retx_round = 0

        self.add_behaviour(self.SyncBehaviour())

#-    class SendInitBehviour(OneShotBehaviour):
#-        async def run(self):
#-
#-            for cnt in range(0, self.agent.get("numagents")):
#-                tojid = F"agent{cnt}@{self.agent.get('server')}"
#-                msg = Message( to=tojid, sender=self.agent.name)
#-                msg.set_metadata("reply_with", str(uuid.uuid4()))   
#-                msg.body = "Start"
#-
#-                logMessage(msg, "S")
#-                await self.send(msg)

    async def send_start(self, recipients):
        for tojid in recipients:
            msg = Message(to=tojid, sender=self.name)
            msg.set_metadata("reply_with", str(uuid.uuid4()))
            msg.body = "Start"
            logMessage(msg, "S")
            await self.send(msg)

    class SyncBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(1)  # short poll
            if msg:
                logMessage(msg, "R")
                sender = str(msg.sender).split("/")[0]
                body = (msg.body or "").strip().upper()
                if body == "READY":
                    self.agent.ready.add(sender)
                elif body == "ACK":
                    self.agent.acked.add(sender)

            now = time.time()

            # Barrier: wait for READY (or timeout), then send START once
            if (not self.agent.start_sent) and (
                len(self.agent.ready) >= self.agent.numagents or now >= self.agent.ready_deadline
            ):
                missing = self.agent.numagents - len(self.agent.ready)
                logInfoMessage(
                    f"READY barrier: {len(self.agent.ready)}/{self.agent.numagents} (missing {missing}). Sending START.",
                    self.agent.name,
                )
                await self.agent.send_start(self.agent.all_agents)
                self.agent.start_sent = True
                self.agent.next_retx_ts = now + self.agent.retx_interval_s

            # ACK tracking + retransmits to missing ACKs
            if self.agent.start_sent:
                if len(self.agent.acked) >= self.agent.numagents:
                    logInfoMessage("All ACK received. Done.", self.agent.name)
                    self.kill()
                    return

                if now >= (self.agent.next_retx_ts or 0) and self.agent.retx_round < self.agent.max_retx_rounds:
                    missing_agents = [jid for jid in self.agent.all_agents if jid not in self.agent.acked]
                    logInfoMessage(
                        f"Retransmit START round {self.agent.retx_round + 1}/{self.agent.max_retx_rounds} "
                        f"to {len(missing_agents)} missing ACK.",
                        self.agent.name,
                    )
                    await self.agent.send_start(missing_agents)
                    self.agent.retx_round += 1
                    self.agent.next_retx_ts = now + self.agent.retx_interval_s