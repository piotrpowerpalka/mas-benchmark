#!/usr/bin/env python3
"""Configure and start the uAgents benchmark."""

import argparse

from uagents import Bureau
from uagents.resolver import RulesBasedResolver
from uagents_core.identity import Identity

from cfpAgent import CfpAgent
from informAgent import InformAgent
from queryAgent import QueryAgent
from startup import StartupBarrier
from tools import log_init, seed_phrase


MESSAGE_PORT = 8000
READINESS_PORT = 8001
READINESS_TIMEOUT_SECONDS = 60.0
AGENT_CLASSES = {
    "inform": InformAgent,
    "query": QueryAgent,
    "cfp": CfpAgent,
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the uAgents benchmark.")
    parser.add_argument("--agent-count", type=int, required=True)
    parser.add_argument("--container-count", type=int, required=True)
    parser.add_argument("--container-index", type=int, required=True)
    parser.add_argument("--workload", choices=tuple(AGENT_CLASSES), required=True)
    parser.add_argument(
        "--transport",
        choices=("local", "agentverse"),
        default="local",
    )
    parser.add_argument("--repeats", type=int, required=True)
    parser.add_argument("--message-size", type=int, required=True)
    parser.add_argument("--group-size", type=int, required=True)
    parser.add_argument("--period-ms", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--port", type=int, default=MESSAGE_PORT)
    parser.add_argument("--readiness-port", type=int, default=READINESS_PORT)
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=READINESS_TIMEOUT_SECONDS,
    )
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


def _container_for_agent(agent_id, args):
    return min(
        ((agent_id + 1) * args.container_count - 1) // args.agent_count,
        args.container_count - 1,
    )


def main(argv=None):
    args = parse_args(argv)
    first_agent_id = args.container_index * args.agent_count // args.container_count
    after_last_agent_id = (
        (args.container_index + 1) * args.agent_count // args.container_count
    )
    address_by_id = {
        agent_id: Identity.from_seed(seed_phrase(args.seed, agent_id), 0).address
        for agent_id in range(args.agent_count)
    }
    name_by_address = {
        address: "agent{}".format(agent_id)
        for agent_id, address in address_by_id.items()
    }
    if args.transport == "agentverse":
        resolver = None
    else:
        endpoints = {
            address: "http://mas{}:{}/submit".format(
                _container_for_agent(agent_id, args),
                args.port,
            )
            for agent_id, address in address_by_id.items()
        }
        resolver = RulesBasedResolver(endpoints)
    startup_barrier = StartupBarrier(
        args,
        first_agent_id,
        after_last_agent_id - first_agent_id,
    )
    agent_class = AGENT_CLASSES[args.workload]
    agents = []

    for agent_id in range(first_agent_id, after_last_agent_id):
        log_init("initializing", "agent{}".format(agent_id))
        agent_class_instance = agent_class(
            agent_id=agent_id,
            args=args,
            address_by_id=address_by_id,
            name_by_address=name_by_address,
            resolver=resolver,
            startup_barrier=startup_barrier,
        )
        agents.append(agent_class_instance)

    Bureau(agents, port=args.port).run()


if __name__ == "__main__":
    main()
