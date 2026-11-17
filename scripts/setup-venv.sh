#!/usr/bin/env bash
set -eu

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${1:-$ROOT_DIR/.venv}"

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt"

echo "Virtual environment ready at: $VENV_DIR"
