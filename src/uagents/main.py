#!/usr/bin/env python3
"""Run the uAgents workloads used by the benchmark."""

import argparse
import asyncio
from contextlib import suppress
from datetime import datetime
import random
import string
import uuid

from uagents import Agent, Bureau, Context, Model
from uagents.resolver import RulesBasedResolver
from uagents_core.identity import Identity
from uagents_core.types import DeliveryStatus


MESSAGE_PORT = 8000
READINESS_PORT = 8001
READINESS_TIMEOUT_SECONDS = 60.0
CONNECT_TIMEOUT_SECONDS = 0.25
ALPHANUMERIC = string.ascii_letters + string.digits


class BenchmarkMessage(Model):
    performative: str
    reply_with: str
    conversation_id: str
    payload: str


class BenchmarkAgent(Agent):
    async def _update_agent_status(self, active: bool) -> None:
        # Static in-network routes make external agent-status updates unnecessary.
        del active
        return None


def _seed_phrase(seed, agent_id):
    return "mas-benchmark-uagents-{}-agent-{}".format(seed, agent_id)


def _timestamp():
    return datetime.now().isoformat(timespec="microseconds")


def _log_init(state, agent_name):
    print("init;{};{};{}".format(state, agent_name, _timestamp()), flush=True)


def _log_message(sender, recipient, performative, reply_with, conversation_id, direction):
    print(
        "{};{};{};{};{};{};{}".format(
            sender,
            recipient,
            performative,
            reply_with,
            conversation_id,
            direction,
            _timestamp(),
        ),
        flush=True,
    )


async def _close_readiness_connection(reader, writer):
    del reader
    writer.close()
    with suppress(OSError):
        await writer.wait_closed()


async def _tcp_port_ready(host, port):
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=CONNECT_TIMEOUT_SECONDS,
        )
    except (OSError, asyncio.TimeoutError):
        return False

    writer.close()
    with suppress(OSError):
        await writer.wait_closed()
    return True


async def _wait_for_all_containers(args):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + args.startup_timeout

    while not await _tcp_port_ready("127.0.0.1", args.port):
        if loop.time() >= deadline:
            raise TimeoutError("uAgents message server did not start")
        await asyncio.sleep(0.1)

    server = await asyncio.start_server(
        _close_readiness_connection,
        host="0.0.0.0",
        port=args.readiness_port,
    )
    try:
        while True:
            pending = []
            for container_id in range(args.container_count):
                if container_id == args.container_index:
                    continue
                if not await _tcp_port_ready(
                    "mas{}".format(container_id), args.readiness_port
                ):
                    pending.append(container_id)

            if not pending:
                return server
            if loop.time() >= deadline:
                raise TimeoutError(
                    "uAgents containers did not become ready: {}".format(pending)
                )
            await asyncio.sleep(0.1)
    except Exception:
        server.close()
        await server.wait_closed()
        raise


def _random_payload(rng, size):
    return "".join(rng.choices(ALPHANUMERIC, k=size))


def _add_agent_behaviours(
    agent,
    agent_id,
    args,
    local_agents_ready,
    startup_state,
    readiness_servers,
    name_by_address,
    address_by_id,
    addresses_by_container,
):
    rng = random.Random(args.seed + agent_id)
    pending_cfp = {}
    other_addresses = [
        address for address in address_by_id.values() if address != agent.address
    ]

    async def send_message(ctx, recipient_address, performative, conversation_id):
        reply_with = "rw-{}".format(uuid.uuid4())
        payload = _random_payload(rng, args.message_size)
        recipient_name = name_by_address[recipient_address]
        message = BenchmarkMessage(
            performative=performative,
            reply_with=reply_with,
            conversation_id=conversation_id,
            payload=payload,
        )
        _log_message(
            agent.name,
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
                agent.name,
                recipient_name,
                performative,
                status,
            )

    async def send_inform(ctx):
        recipient = rng.choice(other_addresses)
        conversation_id = "cid-{}".format(uuid.uuid4())
        await send_message(ctx, recipient, "inform", conversation_id)

    async def send_query(ctx):
        recipient = rng.choice(other_addresses)
        conversation_id = "cid-{}".format(uuid.uuid4())
        await send_message(ctx, recipient, "query", conversation_id)

    async def send_cfp(ctx):
        recipients = rng.sample(
            other_addresses,
            k=min(args.group_size, len(other_addresses)),
        )
        conversation_id = "cid-{}".format(uuid.uuid4())
        pending_cfp[conversation_id] = {
            "expected": set(recipients),
            "responses": {},
        }
        for recipient in recipients:
            await send_message(ctx, recipient, "cfp", conversation_id)

    async def start_workload(ctx: Context):
        if agent_id == addresses_by_container[args.container_index][0]:
            try:
                server = await _wait_for_all_containers(args)
                readiness_servers.append(server)
                startup_state["ready"] = True
            except (OSError, TimeoutError, asyncio.TimeoutError) as error:
                ctx.logger.error("uAgents readiness barrier failed: %s", error)
            finally:
                local_agents_ready.set()
        else:
            await local_agents_ready.wait()

        if not startup_state["ready"]:
            return

        _log_init("running", agent.name)
        await asyncio.sleep(args.period_ms / 1000.0)
        for repetition in range(args.repeats):
            if args.workload == "inform":
                await send_inform(ctx)
            elif args.workload == "query":
                await send_query(ctx)
            else:
                await send_cfp(ctx)

            if repetition + 1 < args.repeats:
                await asyncio.sleep(args.period_ms / 1000.0)

    @agent.on_event("startup")
    async def on_startup(ctx: Context):
        await start_workload(ctx)

    @agent.on_message(model=BenchmarkMessage)
    async def on_message(ctx: Context, sender: str, message: BenchmarkMessage):
        sender_name = name_by_address.get(sender)
        if sender_name is None:
            ctx.logger.error("Received a benchmark message from unknown agent %s", sender)
            return

        _log_message(
            sender_name,
            agent.name,
            message.performative,
            message.reply_with,
            message.conversation_id,
            "R",
        )

        if args.workload == "query" and message.performative == "query":
            await send_message(
                ctx,
                sender,
                "inform",
                message.conversation_id,
            )
        elif args.workload == "cfp":
            if message.performative == "cfp":
                performative = "propose" if rng.random() < 0.9 else "refuse"
                await send_message(
                    ctx,
                    sender,
                    performative,
                    message.conversation_id,
                )
            elif message.performative in ("propose", "refuse"):
                round_state = pending_cfp.get(message.conversation_id)
                if (
                    round_state is None
                    or sender not in round_state["expected"]
                    or sender in round_state["responses"]
                ):
                    return

                round_state["responses"][sender] = message.performative
                if round_state["responses"].keys() != round_state["expected"]:
                    return

                del pending_cfp[message.conversation_id]
                proposers = [
                    address
                    for address, response in round_state["responses"].items()
                    if response == "propose"
                ]
                if proposers:
                    winner = rng.choice(proposers)
                    await send_message(
                        ctx,
                        winner,
                        "accept-proposal",
                        message.conversation_id,
                    )
                    for proposer in proposers:
                        if proposer != winner:
                            await send_message(
                                ctx,
                                proposer,
                                "reject-proposal",
                                message.conversation_id,
                            )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the uAgents benchmark.")
    parser.add_argument("--agent-count", type=int, required=True)
    parser.add_argument("--container-count", type=int, required=True)
    parser.add_argument("--container-index", type=int, required=True)
    parser.add_argument("--workload", choices=("inform", "query", "cfp"), required=True)
    parser.add_argument("--repeats", type=int, required=True)
    parser.add_argument("--message-size", type=int, required=True)
    parser.add_argument("--group-size", type=int, required=True)
    parser.add_argument("--period-ms", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--port", type=int, default=MESSAGE_PORT)
    parser.add_argument("--readiness-port", type=int, default=READINESS_PORT)
    parser.add_argument("--startup-timeout", type=float, default=READINESS_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)

    if args.agent_count < 2:
        parser.error("--agent-count must be at least 2")
    if not 1 <= args.container_count <= args.agent_count:
        parser.error("--container-count must be between 1 and --agent-count")
    if not 0 <= args.container_index < args.container_count:
        parser.error("--container-index is outside the configured container range")
    if args.repeats < 0 or args.message_size < 0:
        parser.error("--repeats and --message-size must be non-negative")
    if args.group_size <= 0 or args.period_ms <= 0:
        parser.error("--group-size and --period-ms must be positive")
    if args.port == args.readiness_port:
        parser.error("--port and --readiness-port must be different")
    if args.startup_timeout <= 0:
        parser.error("--startup-timeout must be positive")
    return args


def main(argv=None):
    args = parse_args(argv)
    first_agent_id = args.container_index * args.agent_count // args.container_count
    after_last_agent_id = (
        (args.container_index + 1) * args.agent_count // args.container_count
    )

    address_by_id = {
        agent_id: Identity.from_seed(_seed_phrase(args.seed, agent_id), 0).address
        for agent_id in range(args.agent_count)
    }
    name_by_address = {
        address: "agent{}".format(agent_id)
        for agent_id, address in address_by_id.items()
    }
    addresses_by_container = {
        container_id: [] for container_id in range(args.container_count)
    }
    endpoints = {}
    for agent_id, address in address_by_id.items():
        container_id = min(
            ((agent_id + 1) * args.container_count - 1) // args.agent_count,
            args.container_count - 1,
        )
        addresses_by_container[container_id].append(agent_id)
        endpoints[address] = "http://mas{}:{}/submit".format(
            container_id, args.port
        )
    resolver = RulesBasedResolver(endpoints)
    local_agents_ready = asyncio.Event()
    startup_state = {"ready": False}
    readiness_servers = []
    agents = []

    for agent_id in range(first_agent_id, after_last_agent_id):
        name = "agent{}".format(agent_id)
        _log_init("initializing", name)
        agent = BenchmarkAgent(
            name=name,
            seed=_seed_phrase(args.seed, agent_id),
            port=args.port,
            resolve=resolver,
            enable_agent_inspector=False,
            report_events=False,
            mark_inactive_on_shutdown=False,
        )
        _add_agent_behaviours(
            agent,
            agent_id,
            args,
            local_agents_ready,
            startup_state,
            readiness_servers,
            name_by_address,
            address_by_id,
            addresses_by_container,
        )
        agents.append(agent)

    Bureau(agents, port=args.port).run()


if __name__ == "__main__":
    main()
