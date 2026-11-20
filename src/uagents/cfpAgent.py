from benchmarkAgent import BenchmarkAgent
from tools import new_conversation_id


class CfpAgent(BenchmarkAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending_cfp = {}

    async def send_periodic_message(self, ctx):
        recipients = self.rng.sample(
            self.other_addresses,
            k=min(self.args.group_size, len(self.other_addresses)),
        )
        conversation_id = new_conversation_id()
        self.pending_cfp[conversation_id] = {
            "expected": set(recipients),
            "responses": {},
        }
        for recipient in recipients:
            await self.send_benchmark_message(
                ctx,
                recipient,
                "cfp",
                conversation_id,
            )

    async def handle_benchmark_message(self, ctx, sender, message):
        if message.performative == "cfp":
            performative = "propose" if self.rng.random() < 0.9 else "refuse"
            await self.send_benchmark_message(
                ctx,
                sender,
                performative,
                message.conversation_id,
            )
        elif message.performative in ("propose", "refuse"):
            await self._collect_response(ctx, sender, message)

    async def _collect_response(self, ctx, sender, message):
        round_state = self.pending_cfp.get(message.conversation_id)
        if (
            round_state is None
            or sender not in round_state["expected"]
            or sender in round_state["responses"]
        ):
            return

        round_state["responses"][sender] = message.performative
        if round_state["responses"].keys() != round_state["expected"]:
            return

        del self.pending_cfp[message.conversation_id]
        proposers = [
            address
            for address, response in round_state["responses"].items()
            if response == "propose"
        ]
        if not proposers:
            return

        winner = self.rng.choice(proposers)
        await self.send_benchmark_message(
            ctx,
            winner,
            "accept-proposal",
            message.conversation_id,
        )
        for proposer in proposers:
            if proposer != winner:
                await self.send_benchmark_message(
                    ctx,
                    proposer,
                    "reject-proposal",
                    message.conversation_id,
                )
