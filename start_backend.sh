#!/bin/bash

# Check if port 8000 is in use
if lsof -i :8000; then
    echo "Port 8000 is in use, freeing it..."
    PID=$(lsof -t -i :8000)
    if [ -n "$PID" ]; then
        echo "Killing process $PID"
        kill -9 $PID
    fi
else
    echo "Port 8000 is free, starting the backend server..."
fi

# Determine the number of workers based on CPU cores using python3
WORKERS=$(python3 -c 'import multiprocessing as mp; print(mp.cpu_count() * 2 + 1)')

gunicorn backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers $WORKERS \
    --timeout 300 \
    --log-level=debug \
    --access-logfile - \
    --error-logfile -
