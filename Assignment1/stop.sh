#!/bin/bash

echo "🛑 Stopping BKLV File Sharing System..."

if [ -f ".pids" ]; then
    PIDS=$(cat .pids)
    for PID in $PIDS; do
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID 2>/dev/null
            echo "✅ Stopped process $PID"
        fi
    done
    rm .pids
else
    # Try to kill by port
    echo "Killing processes by port..."
    lsof -ti:9000 | xargs kill -9 2>/dev/null
    lsof -ti:5500 | xargs kill -9 2>/dev/null
    lsof -ti:5501 | xargs kill -9 2>/dev/null
    lsof -ti:3000 | xargs kill -9 2>/dev/null
fi

echo "✅ All services stopped"
