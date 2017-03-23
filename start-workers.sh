#!/bin/bash
# Get script file location
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Go there
cd $DIR/scanner

# Start workers in background
echo "Starting scanner worker"
screen -d -m -S celery-browser-scan celery -A scanner.scan_connector worker -Q browser-scan    --hostname ffscan@%h   --concurrency 1
echo "Starting DB insert worker"
screen -d -m -S celery-mongo-insert celery -A scanner.db_connector   worker -Q db-mongo-access --hostname dbworker@%h --concurrency 1  # TODO Update concurrency level