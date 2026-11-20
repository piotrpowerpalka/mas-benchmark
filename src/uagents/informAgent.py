from benchmarkAgent import BenchmarkAgent
from tools import new_conversation_id


class InformAgent(BenchmarkAgent):
    async def send_periodic_message(self, ctx):
        recipient = self.rng.choice(self.other_addresses)
        await self.send_benchmark_message(
            ctx,
            recipient,
            "inform",
            new_conversation_id(),
        )
