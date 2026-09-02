#!/usr/bin/env bash
# TRACE Migrate Wrapper Script
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$ROOT_DIR/start.sh" migrate "$@"
