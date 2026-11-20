import asyncio
import random

from uagents import Agent, Context
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
        super().__init__(
            name="agent{}".format(agent_id),
            seed=seed_phrase(args.seed, agent_id),
            port=args.port,
            resolve=resolver,
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
        # Static in-network routes make external agent-status updates unnecessary.
        del active
        return None

    async def _benchmark_startup_handler(self, ctx: Context):
        if not await self.startup_barrier.wait(self.agent_id, ctx.logger):
            return

        log_init("running", self.name)
        await asyncio.sleep(self.args.period_ms / 1000.0)
        for repetition in range(self.args.repeats):
            await self.send_periodic_message(ctx)
            if repetition + 1 < self.args.repeats:
                await asyncio.sleep(self.args.period_ms / 1000.0)

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
