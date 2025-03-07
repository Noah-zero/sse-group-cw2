#!/bin/sh

if [ -z "$CLIENT_XUNFEI_API_KEY" ]; then
  echo "ERROR: API key not found!"
  exit 1
fi

echo "Using API key: $CLIENT_XUNFEI_API_KEY"

export PYTHONPATH=/app
echo "PYTHONPATH is set to: $PYTHONPATH"
ls -l /app

echo "Recursive structure of /app:"
tree /app || find /app  # Use `tree` if available, otherwise use `find`

exec python -m chat.deepseek