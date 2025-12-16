#!/usr/bin/env bash

CONTAINERS=${1:-"1"}


XMPP="prosody"  # prosody | tigase
NUM_AGENTS="30"
REPEATS="100"
MESSAGE_SIZE=$((1024))
COMM_TYPE="inform"
GROUP_SIZE="30"
MEMSIZE="512mb" # smallcase - beacuse the docker name uses it that way
CPUS="2"

LOGDIR="logs_$XMPP-c$CONTAINERS-n$NUM_AGENTS-r$REPEATS-ms$MESSAGE_SIZE-$COMM_TYPE-g$GROUP_SIZE-m$MEMSIZE-cpu$CPUS"

mkdir -p "$LOGDIR" || exit 1
mkdir -p "$LOGDIR/prosody"
mkdir -p "$LOGDIR/tigase"
cp prosody/* "$LOGDIR/prosody"/. -r
cp tigase/* "$LOGDIR/tigase"/. -r
cp Dockerfile "$LOGDIR"/.
cp src-agents/* "$LOGDIR"/. -r 

cd "$LOGDIR" || exit 1

DOCKER_COMPOSE_NAME="docker-compose-$XMPP-c$CONTAINERS-n$NUM_AGENTS-r$REPEATS-ms$MESSAGE_SIZE-$COMM_TYPE-g$GROUP_SIZE-m$MEMSIZE-cpu$CPUS.yaml"

echo "Generating docker compose file: $DOCKER_COMPOSE_NAME"
python3 ../gen_compose.py "$DOCKER_COMPOSE_NAME" "$XMPP" "$CONTAINERS" "$NUM_AGENTS" "$REPEATS" "$MESSAGE_SIZE" "$COMM_TYPE" "$GROUP_SIZE" "$MEMSIZE" "$CPUS"

docker compose -f "$DOCKER_COMPOSE_NAME" up > "logs_$DOCKER_COMPOSE_NAME.log" 2>&1 &

for ((i=0; i<CONTAINERS; i++)); do
    CNT="$LOGDIR-mas$i-1"
    echo "Starting container $CNT"
    ../mem.sh $CNT "mem_$DOCKER_COMPOSE_NAME-$CNT.log" &
    PID=$!
    echo "Process ID for container $CNT: $PID" >> "process_ids.log"
    echo "Running container $CNT"
done

# Wait until the log file stops growing
LAST_SIZE=0
STABLE_COUNT=0
while [ $STABLE_COUNT -lt 3 ]; do
    sleep 2
    CURRENT_SIZE=$(stat -f%z "logs_$DOCKER_COMPOSE_NAME.log" 2>/dev/null || stat -c%s "logs_$DOCKER_COMPOSE_NAME.log" 2>/dev/null)
    if [ "$CURRENT_SIZE" -eq "$LAST_SIZE" ]; then
        ((STABLE_COUNT++))
    else
        STABLE_COUNT=0
    fi
    LAST_SIZE="$CURRENT_SIZE"
done
sleep 1

docker compose -f "$DOCKER_COMPOSE_NAME" down


# Stop the memory logging processes
pkill -f "../mem.sh $LOGDIR-mas"

python3 ../process_res.py "logs_$DOCKER_COMPOSE_NAME.log"
for ((i=0; i<CONTAINERS; i++)); do
    python3 ../process_mem.py "mem_$DOCKER_COMPOSE_NAME-mas$i-1.log"
done

cd ..

