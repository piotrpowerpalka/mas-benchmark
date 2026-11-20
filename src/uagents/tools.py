from datetime import datetime
import string
import uuid

from uagents import Model


ALPHANUMERIC = string.ascii_letters + string.digits


class BenchmarkMessage(Model):
    performative: str
    reply_with: str
    conversation_id: str
    payload: str


def seed_phrase(seed, agent_id):
    return "mas-benchmark-uagents-{}-agent-{}".format(seed, agent_id)


def new_reply_with():
    return "rw-{}".format(uuid.uuid4())


def new_conversation_id():
    return "cid-{}".format(uuid.uuid4())


def random_payload(rng, size):
    return "".join(rng.choices(ALPHANUMERIC, k=size))


def _timestamp():
    return datetime.now().isoformat(timespec="microseconds")


def log_init(state, agent_name):
    print("init;{};{};{}".format(state, agent_name, _timestamp()), flush=True)


def log_message(sender, recipient, performative, reply_with, conversation_id, direction):
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
