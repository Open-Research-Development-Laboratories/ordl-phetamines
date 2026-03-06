#!/bin/bash
set -euo pipefail
if [ $# -eq 0 ]; then echo "Usage: Provide C source code"; exit 1; fi
if [ "$1" = "--code" ]; then echo "$2" > /sandbox/main.c; fi
gcc -std=c23 -O2 -o /sandbox/program /sandbox/main.c 2>&1
timeout 10s /sandbox/program 2>&1 || echo "Exit code: $?"
