#!/bin/bash
# Get script file location
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Go there
cd $DIR/scanner

# Start workers in background
echo "Starting browser scanner worker"
screen -d -m -S celery-browser-scan celery  -A scanner.scan_connector worker -Q scan-browser           --hostname ffscan@%h    --concurrency 1
echo "Starting external scanner worker"
screen -d -m -S celery-external-scan celery -A scanner.externaltests_connector worker -Q scan-external --hostname extscan@%h   --concurrency 3  # TODO Update concurrency level
