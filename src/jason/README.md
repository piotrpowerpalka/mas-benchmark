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

## How to run

Run one scenario at a time:

```bash
jason benchmark_inform.mas2j
jason benchmark_query.mas2j
jason benchmark_cfp.mas2j
```

## What is preserved

- init agent that starts all workers,
- repetitions counter,
- random recipient selection,
- request/reply flow for `query`,
- simplified CFP / propose / refuse / accept / reject flow,
- CSV-like console logging.

## Deliberate adaptation

In SPADE the body was a random alphanumeric string of a configured byte size. In this Jason version the body is represented symbolically as `payload(Size, Stamp)`. This preserves the protocol shape and the size parameter in a Jason-friendly way without adding Java helper classes.
