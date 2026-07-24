#!/usr/bin/env bash

cd "$(dirname "$0")/.." || exit 1
mkdir -p "$HOME/.local/state/hwlogger"

exec ./scripts/run-dev.sh \
  >> "$HOME/.local/state/hwlogger/launcher.log" 2>&1
