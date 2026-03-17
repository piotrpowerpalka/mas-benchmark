#!/usr/bin/env bash

CONTAINERS=${1:-"1"}
XMPP=${2:-"prosody"} # prosody | tigase | jade
COMM_TYPE=${3:-"inform"} # inform | query | cfp
NUM_AGENTS=${4:-"100"}
REPEATS=${5:-"100"}
MESSAGE_SIZE=${6:-$((1024))}
RECOMPILE=${7:-"false"} # true | false
GROUP_SIZE=${8:-"10"}

MEMSIZE="1GB"
CPUS="1"

mkdir -p logs  || exit 1
cd logs || exit 1

LOGDIR="logs_$XMPP-c$CONTAINERS-n$NUM_AGENTS-r$REPEATS-ms$MESSAGE_SIZE-$COMM_TYPE-g$GROUP_SIZE-m$MEMSIZE-cpu$CPUS"

mkdir -p "$LOGDIR" || exit 1

if [ "$XMPP" == "prosody" ] || [ "$XMPP" == "tigase" ]; then
    mkdir -p "$LOGDIR/prosody"
    mkdir -p "$LOGDIR/tigase"
    cp ../src/spade/prosody/* "$LOGDIR/prosody"/. -r
    cp ../src/spade/tigase/* "$LOGDIR/tigase"/. -r
    cp ../dockers/Dockerfile.spade "$LOGDIR"/Dockerfile
    cp ../src/spade/*.py "$LOGDIR"/. -r 
fi

if [ "$XMPP" == "jade" ]; then
    mkdir -p "$LOGDIR/lib"
    mkdir -p "$LOGDIR/jade"
    cp ../src/jade/* "$LOGDIR"/jade/. -r
    cp ../lib/jade.jar "$LOGDIR"/lib/. -r
    cp ../dockers/Dockerfile.jade "$LOGDIR"/Dockerfile
fi

cd "$LOGDIR" || exit 1

DOCKER_COMPOSE_NAME="docker-compose-$XMPP-c$CONTAINERS-n$NUM_AGENTS-r$REPEATS-ms$MESSAGE_SIZE-$COMM_TYPE-g$GROUP_SIZE-m$MEMSIZE-cpu$CPUS.yaml"

echo "Generating docker compose file: $DOCKER_COMPOSE_NAME"
python3 ../../scripts/gen_compose.py "$DOCKER_COMPOSE_NAME" "$XMPP" "$CONTAINERS" "$NUM_AGENTS" "$REPEATS" "$MESSAGE_SIZE" "$COMM_TYPE" "$GROUP_SIZE" "$MEMSIZE" "$CPUS"

if [ "$RECOMPILE" == "true" ]; then
    echo "Recompiling docker images"
    docker compose -f "$DOCKER_COMPOSE_NAME" build --no-cache
fi
docker compose -f "$DOCKER_COMPOSE_NAME" up > "logs_$DOCKER_COMPOSE_NAME.log" 2>&1 &

for ((i=0; i<CONTAINERS; i++)); do
    CNT="mas$i"
    echo "Starting container $CNT"
    ../../scripts/mem.sh $CNT "mem_$DOCKER_COMPOSE_NAME-$CNT.log" &
    PID=$!
    echo "Process ID for container $CNT: $PID" >> "process_ids.log"
    echo "Running container $CNT"
done

../../scripts/mem.sh serverhello "mem_$DOCKER_COMPOSE_NAME-xmpp.log" &


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
pkill -f "../../scripts/mem.sh $LOGDIR-mas"

python3 ../../scripts/process_res.py "logs_$DOCKER_COMPOSE_NAME.log"
for ((i=0; i<CONTAINERS; i++)); do
    CNT="mas$i"
    python3 ../../scripts/process_mem.py "mem_$DOCKER_COMPOSE_NAME-$CNT.log"
done

python3 ../../scripts/process_mem.py "mem_$DOCKER_COMPOSE_NAME-xmpp.log"

cd ../..

