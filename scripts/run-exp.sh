#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CONTAINERS=${1:-"1"}
XMPP=${2:-"prosody"} # prosody | tigase | jade | jason | uagents | uagents-agentverse
COMM_TYPE=${3:-"inform"} # inform | query | cfp
NUM_AGENTS=${4:-"100"}
REPEATS=${5:-"100"}
MESSAGE_SIZE=${6:-$((1024))}
RECOMPILE=${7:-"false"} # true | false
GROUP_SIZE=${8:-"10"}
PERIOD=${9:-"100"} # in milliseconds
SEED=${10:-"213742189290"}

if [ "$XMPP" == "uagents-agentverse" ] && [ -z "${AGENTVERSE_API_TOKEN:-}" ]; then
    echo "Set AGENTVERSE_API_TOKEN to run uAgents with Agentverse transport." >&2
    exit 1
fi

MEMSIZE="1GB"
CPUS="1"

mkdir -p "$ROOT_DIR/logs" || exit 1
cd "$ROOT_DIR/logs" || exit 1

LOGDIR="logs_$XMPP-c$CONTAINERS-n$NUM_AGENTS-r$REPEATS-ms$MESSAGE_SIZE-$COMM_TYPE-g$GROUP_SIZE-m$MEMSIZE-cpu$CPUS-p$PERIOD-seed$SEED"

mkdir -p "$LOGDIR" || exit 1

if [ "$XMPP" == "prosody" ] || [ "$XMPP" == "tigase" ]; then
    mkdir -p "$LOGDIR/prosody"
    mkdir -p "$LOGDIR/tigase"
    cp "$ROOT_DIR"/src/spade/prosody/* "$LOGDIR/prosody"/. -r
    cp "$ROOT_DIR"/src/spade/tigase/* "$LOGDIR/tigase"/. -r
    cp "$ROOT_DIR/dockers/Dockerfile.spade" "$LOGDIR"/Dockerfile
    cp "$ROOT_DIR"/src/spade/*.py "$LOGDIR"/. -r
fi

if [ "$XMPP" == "jade" ]; then
    mkdir -p "$LOGDIR/lib"
    mkdir -p "$LOGDIR/jade"
    cp "$ROOT_DIR"/src/jade/* "$LOGDIR"/jade/. -r
    cp "$ROOT_DIR/lib/jade.jar" "$LOGDIR"/lib/. -r
    cp "$ROOT_DIR/dockers/Dockerfile.jade" "$LOGDIR"/Dockerfile
fi

if [ "$XMPP" == "jason" ]; then
    mkdir -p "$LOGDIR/lib"
    mkdir -p "$LOGDIR/jade"
    cp "$ROOT_DIR"/src/jade/* "$LOGDIR"/jade/. -r
    cp "$ROOT_DIR/lib/jade.jar" "$LOGDIR"/lib/. -r
    cp "$ROOT_DIR/dockers/Dockerfile.jade" "$LOGDIR"/Dockerfile.jade
    cp "$ROOT_DIR/dockers/Dockerfile.jason" "$LOGDIR"/Dockerfile.jason
fi

if [ "$XMPP" == "uagents" ] || [ "$XMPP" == "uagents-agentverse" ]; then
    cp "$ROOT_DIR"/src/uagents/*.py "$LOGDIR"/.
    cp "$ROOT_DIR/src/uagents/requirements.txt" "$LOGDIR"/requirements.txt
    cp "$ROOT_DIR/dockers/Dockerfile.uagents" "$LOGDIR"/Dockerfile.uagents
fi

cd "$LOGDIR" || exit 1

DOCKER_COMPOSE_NAME="docker-compose-$XMPP-c$CONTAINERS-n$NUM_AGENTS-r$REPEATS-ms$MESSAGE_SIZE-$COMM_TYPE-g$GROUP_SIZE-m$MEMSIZE-cpu$CPUS-p$PERIOD-seed$SEED.yaml"

echo "Generating docker compose file: $DOCKER_COMPOSE_NAME"
python3 "$ROOT_DIR/scripts/gen_compose.py" "$DOCKER_COMPOSE_NAME" "$XMPP" "$CONTAINERS" "$NUM_AGENTS" "$REPEATS" "$MESSAGE_SIZE" "$COMM_TYPE" "$GROUP_SIZE" "$MEMSIZE" "$CPUS" "$PERIOD" "$SEED"

if [ "$RECOMPILE" == "true" ]; then
    echo "Recompiling docker images"
    docker compose -f "$DOCKER_COMPOSE_NAME" build --no-cache
fi
docker compose -f "$DOCKER_COMPOSE_NAME" up --build > "logs_$DOCKER_COMPOSE_NAME.log" 2>&1 &

for ((i=0; i<CONTAINERS; i++)); do
    CNT="mas$i"
    echo "Starting container $CNT"
    "$ROOT_DIR/scripts/mem.sh" "$CNT" "mem_$DOCKER_COMPOSE_NAME-$CNT.log" &
    PID=$!
    echo "Process ID for container $CNT: $PID" >> "process_ids.log"
    echo "Running container $CNT"
done

if [ "$XMPP" != "uagents" ] && [ "$XMPP" != "uagents-agentverse" ]; then
    "$ROOT_DIR/scripts/mem.sh" serverhello "mem_$DOCKER_COMPOSE_NAME-xmpp.log" &
fi


# Wait until the log file stops growing
LAST_SIZE=0
STABLE_COUNT=0
while [ $STABLE_COUNT -lt 3 ]; do
    sleep 10
    CURRENT_SIZE=$(stat -f%z "logs_$DOCKER_COMPOSE_NAME.log" 2>/dev/null || stat -c%s "logs_$DOCKER_COMPOSE_NAME.log" 2>/dev/null)
    if [ "$CURRENT_SIZE" -eq "$LAST_SIZE" ]; then
        ((STABLE_COUNT++))
    else
        STABLE_COUNT=0
    fi
    LAST_SIZE="$CURRENT_SIZE"
done
sleep 5

docker compose -f "$DOCKER_COMPOSE_NAME" down

# Stop the memory logging processes
pkill -f "$ROOT_DIR/scripts/mem.sh"

OUTPUT_LOG="$ROOT_DIR/logs/$LOGDIR/logs_$DOCKER_COMPOSE_NAME.log"
python3 "$ROOT_DIR/scripts/process_res.py" "$OUTPUT_LOG"
for ((i=0; i<CONTAINERS; i++)); do
    CNT="mas$i"
    python3 "$ROOT_DIR/scripts/process_mem.py" "$ROOT_DIR/logs/$LOGDIR/mem_$DOCKER_COMPOSE_NAME-$CNT.log"
done

if [ "$XMPP" != "uagents" ] && [ "$XMPP" != "uagents-agentverse" ]; then
    python3 "$ROOT_DIR/scripts/process_mem.py" "$ROOT_DIR/logs/$LOGDIR/mem_$DOCKER_COMPOSE_NAME-xmpp.log"
fi

cd "$ROOT_DIR"

