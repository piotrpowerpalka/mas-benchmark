# Jason version of the SPADE benchmark

This project is an AgentSpeak/Jason rewrite of the uploaded SPADE benchmark.

## Mapping from SPADE to Jason

- `main.py` -> `benchmark_*.mas2j`
- `initAgent.py` -> `init.asl`
- `informAgent.py` -> `inform.asl`
- `queryAgent.py` -> `query.asl`
- `cfpAgent.py` -> `cfp.asl`
- `tools.py` -> inline logging plans (`!log_send`, `!log_recv`, `!log_init`)

## Important semantic note

Jason does not model SPADE behaviours directly. Instead, the equivalent logic is encoded as:

- initial goals (`!boot`, `!start`),
- plans triggered by message events,
- message exchange via `.send(..., signal, ...)`.

I used `signal` rather than `tell` so that repeated messages always generate a fresh event and are not collapsed by the belief base.

## Run locally with Jason CLI

For local execution, install the Jason CLI and JDK 21, then run one scenario
from this directory:

```bash
jason benchmark_inform.mas2j
jason benchmark_query.mas2j
jason benchmark_cfp.mas2j
```

## Run in Docker

From the repository root in Bash or WSL, run:

```bash
bash scripts/run-exp.sh 2 jason inform 10 10 1024 false 3 100
```

The runner builds a Jason image with JDK 21 and starts Jason agents on the
existing JADE transport, with one JADE main container and the requested number
of Jason agent containers. No Jason CLI, Gradle, or JDK installation is needed
on the host; Docker is required. The workload can be `inform`, `query`, or
`cfp`. The generated MAS project assigns each agent to a container and waits
for all workers to signal readiness before starting the workload. Jason's
inform, query, and CFP workloads initiate the configured number of operations
per agent at the runner's `period` interval. Receivers continue handling
in-flight protocol messages after the final initiation.

## What is preserved

- init agent that starts all workers,
- repetitions counter,
- random recipient selection,
- request/reply flow for `query`,
- simplified CFP / propose / refuse / accept / reject flow,
- CSV-like console logging.

## Deliberate adaptation

Inform payloads are random alphanumeric strings of the configured length, matching the payload content used by JADE and SPADE. Jason includes the protocol identifiers in the message term, so serialized messages have additional framework overhead beyond the payload itself.

Message logs use UUID-based `rw-...` reply identifiers and `cid-...` conversation identifiers, matching the JADE and SPADE log fields.
