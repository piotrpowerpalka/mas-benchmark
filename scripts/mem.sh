#!/usr/bin/env bash

CONTAINER=${1:-mas-benchmark-mas0-1}
OUTFILE=${2:-mem.log}

echo "Logging memory usage of container $CONTAINER to $OUTFILE"

timeout 900 bash -c "until docker ps --format '{{.Names}}' | grep -q \"^${CONTAINER}\$\"; do sleep 1; done"

while :; do
  ts=$(date +%s.%3N) # sekundy z ms
  docker stats --no-stream --format "$ts;{{.Container}};{{.MemUsage}};{{.MemPerc}}" "$CONTAINER" >> "$OUTFILE"
  sleep 0.1
  
  if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    break
  fi
done