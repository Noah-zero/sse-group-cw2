#!/bin/sh

CONTAINER_NAME=$(hostname)
INSTANCE_ID=$(echo "$CONTAINER_NAME" | grep -oE '[0-9]+$' || echo "1")

API_KEY_VAR="CLIENT_XUNFEI_API_KEY_$INSTANCE_ID"
API_KEY=$(eval "echo \$$API_KEY_VAR")

if [ -z "$API_KEY" ]; then
  echo "ERROR: API key for instance $INSTANCE_ID (from $API_KEY_VAR) not found."
  exit 1
fi

export CLIENT_XUNFEI_API_KEY="$API_KEY"

echo "Using API key from variable $API_KEY_VAR for instance $INSTANCE_ID."

exec python deepseek.py
