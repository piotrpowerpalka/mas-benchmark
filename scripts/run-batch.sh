
#!/usr/bin/env bash
set -euo pipefail

# Usage:
# SEEDS_FILE=/path/to/seeds.txt bash scripts/run-batch.sh N command [args...]

if (( $# < 2 )); then
    echo "Usage: $0 N command [args...]"
    exit 1
fi

N="$1"
shift

if ! [[ "$N" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: N must be a positive integer."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEEDS_FILE="${SEEDS_FILE:-$SCRIPT_DIR/seeds.txt}"

if [[ ! -f "$SEEDS_FILE" ]]; then
    echo "Error: Seeds file not found: $SEEDS_FILE"
    exit 1
fi

# Read one seed per line, allowing blank lines and inline comments.
SEEDS=()
LINE_NUMBER=0
while IFS= read -r LINE || [[ -n "$LINE" ]]; do
    ((LINE_NUMBER += 1))

    if (( LINE_NUMBER == 1 )); then
        LINE="${LINE#$'\xef\xbb\xbf'}"
    fi

    LINE="${LINE%%#*}"
    LINE="${LINE#"${LINE%%[![:space:]]*}"}"
    LINE="${LINE%"${LINE##*[![:space:]]}"}"

    if [[ -z "$LINE" ]]; then
        continue
    fi
    if ! [[ "$LINE" =~ ^[0-9]+$ ]]; then
        echo "Error: Invalid seed on line $LINE_NUMBER in $SEEDS_FILE: $LINE" >&2
        exit 1
    fi

    SEEDS+=("$LINE")
done < "$SEEDS_FILE"

if (( ${#SEEDS[@]} < N )); then
    echo "Error: Not enough seeds in $SEEDS_FILE"
    echo "Required: $N, available: ${#SEEDS[@]}"
    exit 1
fi

for (( i=0; i<N; i++ )); do
    SEED="${SEEDS[$i]}"

    echo "========================================"
    echo "Run $((i+1))/$N | Seed: $SEED"
    echo "========================================"

    "$@" "$SEED"

    echo "Completed run $((i+1))/$N"
done

echo "All $N runs completed successfully."
