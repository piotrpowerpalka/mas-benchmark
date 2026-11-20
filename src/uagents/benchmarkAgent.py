import asyncio
import os
import random

from uagents import Agent, Context
from uagents.mailbox import AgentverseConnectRequest, register_in_agentverse
from uagents_core.identity import Identity
from uagents_core.registration import AgentProfile, RegistrationRequest
from uagents_core.types import DeliveryStatus

from tools import (
    BenchmarkMessage,
    log_init,
    log_message,
    new_reply_with,
    random_payload,
    seed_phrase,
)


class BenchmarkAgent(Agent):
    def __init__(
        self,
        agent_id,
        args,
        address_by_id,
        name_by_address,
        resolver,
        startup_barrier,
    ):
        use_agentverse_mailbox = args.transport == "agentverse"
        super().__init__(
            name="agent{}".format(agent_id),
            seed=seed_phrase(args.seed, agent_id),
            port=args.port,
            resolve=None if use_agentverse_mailbox else resolver,
            mailbox=use_agentverse_mailbox,
            enable_agent_inspector=False,
            report_events=False,
            mark_inactive_on_shutdown=False,
        )
        self.agent_id = agent_id
        self.args = args
        self.name_by_address = name_by_address
        self.startup_barrier = startup_barrier
        self.rng = random.Random(args.seed + agent_id)
        self.other_addresses = [
            address for address in address_by_id.values() if address != self.address
        ]

        self.on_event("startup")(self._benchmark_startup_handler)
        self.on_message(model=BenchmarkMessage)(self._benchmark_message_handler)

    async def _update_agent_status(self, active: bool) -> None:
        if self.args.transport == "agentverse":
            await super()._update_agent_status(active)
        else:
            del active

    async def _benchmark_startup_handler(self, ctx: Context):
        if self.args.transport == "agentverse":
            try:
                await self._register_agentverse_mailbox(ctx)
            except Exception as error:
                self.startup_barrier.fail(self.agent_id, error, ctx.logger)
                raise
        if not await self.startup_barrier.wait(self.agent_id, ctx.logger):
            return

        log_init("running", self.name)
        await asyncio.sleep(self.args.period_ms / 1000.0)
        for repetition in range(self.args.repeats):
            await self.send_periodic_message(ctx)
            if repetition + 1 < self.args.repeats:
                await asyncio.sleep(self.args.period_ms / 1000.0)

    async def _register_agentverse_mailbox(self, ctx: Context) -> None:
        user_token = os.environ.get("AGENTVERSE_API_TOKEN")
        if not user_token:
            raise RuntimeError(
                "Set AGENTVERSE_API_TOKEN to enable Agentverse mailbox transport"
            )

        request = AgentverseConnectRequest(
            user_token=user_token,
            agent_type="mailbox",
            team=os.environ.get("AGENTVERSE_TEAM") or None,
        )
        registration = RegistrationRequest(
            address=self.address,
            name=self.name,
            handle=None,
            url=None,
            profile=AgentProfile(),
            endpoints=self.info.endpoints,
            protocols=list(self.protocols.keys()),
            metadata=self.metadata,
        )
        response = await register_in_agentverse(
            request=request,
            identity=Identity.from_seed(
                seed_phrase(self.args.seed, self.agent_id), 0
            ),
            prefix=self.identifier.split("://", 1)[0],
            agentverse=self.agentverse,
            agent_details=registration,
        )
        if not response.success:
            raise RuntimeError(
                "Agentverse mailbox registration failed: {}".format(
                    response.detail or "unspecified error"
                )
            )
        ctx.logger.info("Agentverse mailbox registered for %s", self.name)

    async def _benchmark_message_handler(
        self, ctx: Context, sender: str, message: BenchmarkMessage
    ):
        sender_name = self.name_by_address.get(sender)
        if sender_name is None:
            ctx.logger.error("Received a benchmark message from unknown agent %s", sender)
            return

        log_message(
            sender_name,
            self.name,
            message.performative,
            message.reply_with,
            message.conversation_id,
            "R",
        )
        await self.handle_benchmark_message(ctx, sender, message)

    async def send_periodic_message(self, ctx: Context):
        del ctx
        raise NotImplementedError

    async def handle_benchmark_message(
        self, ctx: Context, sender: str, message: BenchmarkMessage
    ):
        del ctx, sender, message
        return None

    async def send_benchmark_message(
        self, ctx: Context, recipient_address: str, performative: str, conversation_id: str
    ):
        reply_with = new_reply_with()
        recipient_name = self.name_by_address[recipient_address]
        message = BenchmarkMessage(
            performative=performative,
            reply_with=reply_with,
            conversation_id=conversation_id,
            payload=random_payload(self.rng, self.args.message_size),
        )
        log_message(
            self.name,
            recipient_name,
            performative,
            reply_with,
            conversation_id,
            "S",
        )
        status = await ctx.send(recipient_address, message)
        if status.status != DeliveryStatus.DELIVERED:
            ctx.logger.error(
                "Message delivery failed: %s -> %s (%s): %s",
                self.name,
                recipient_name,
                performative,
                status,
            )
