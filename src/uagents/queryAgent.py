from benchmarkAgent import BenchmarkAgent
from tools import new_conversation_id


class QueryAgent(BenchmarkAgent):
    async def send_periodic_message(self, ctx):
        recipient = self.rng.choice(self.other_addresses)
        await self.send_benchmark_message(
            ctx,
            recipient,
            "query",
            new_conversation_id(),
        )

    async def handle_benchmark_message(self, ctx, sender, message):
        if message.performative == "query":
            await self.send_benchmark_message(
                ctx,
                sender,
                "inform",
                message.conversation_id,
            )
