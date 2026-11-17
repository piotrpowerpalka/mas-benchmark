#!/usr/bin/env bash

CONTAINERS=${1:-"1"}
XMPP=${2:-"prosody"} # prosody | tigase
COMM_TYPE=${3:-"inform"} # inform | query | cfp
NUM_AGENTS=${4:-"100"}
REPEATS=${5:-"100"}
MESSAGE_SIZE=${6:-$((1024))}
MEMSIZE=${7:-"512mb"} # smallcase - beacuse the docker name uses it that way
CPUS=${8:-"1"}
GROUP_SIZE=${9:-"30"}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mkdir -p "$ROOT_DIR/logs" || exit 1
cd "$ROOT_DIR/logs" || exit 1

LOGDIR="logs_$XMPP-c$CONTAINERS-n$NUM_AGENTS-r$REPEATS-ms$MESSAGE_SIZE-$COMM_TYPE-g$GROUP_SIZE-m$MEMSIZE-cpu$CPUS"

mkdir -p "$LOGDIR" || exit 1
mkdir -p "$LOGDIR/prosody"
mkdir -p "$LOGDIR/tigase"
cp "$ROOT_DIR"/src/spade/prosody/* "$LOGDIR/prosody"/. -r
cp "$ROOT_DIR"/src/spade/tigase/* "$LOGDIR/tigase"/. -r
cp "$ROOT_DIR"/dockers/Dockerfile.spade "$LOGDIR"/Dockerfile
cp "$ROOT_DIR"/src/spade/*.py "$LOGDIR"/. -r

cd "$LOGDIR" || exit 1

DOCKER_COMPOSE_NAME="docker-compose-$XMPP-c$CONTAINERS-n$NUM_AGENTS-r$REPEATS-ms$MESSAGE_SIZE-$COMM_TYPE-g$GROUP_SIZE-m$MEMSIZE-cpu$CPUS.yaml"

echo "Generating docker compose file: $DOCKER_COMPOSE_NAME"
python3 "$ROOT_DIR/scripts/gen_compose.py" "$DOCKER_COMPOSE_NAME" "$XMPP" "$CONTAINERS" "$NUM_AGENTS" "$REPEATS" "$MESSAGE_SIZE" "$COMM_TYPE" "$GROUP_SIZE" "$MEMSIZE" "$CPUS"

docker compose -f "$DOCKER_COMPOSE_NAME" up --build

