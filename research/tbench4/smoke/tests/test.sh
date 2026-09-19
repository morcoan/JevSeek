#!/bin/bash
set -eu
mkdir -p /logs/verifier
if [ -f /app/result.txt ] && [ "$(cat /app/result.txt)" = 'bonsai_jev_only' ] && [ "$(wc -c < /app/result.txt)" -eq 16 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
