#!/bin/bash

echo "======================================"
echo "BKLV File Sharing System - Quick Start"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if Node is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

echo "✅ Python and Node.js detected"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd bklv-backend
if [ ! -f "requirements.txt" ]; then
    echo "flask==3.0.0" > requirements.txt
    echo "flask-cors==4.0.0" >> requirements.txt
fi
pip3 install -r requirements.txt --quiet
cd ..
echo "✅ Python dependencies installed"
echo ""

# Install Node dependencies
echo "📦 Installing Node.js dependencies..."
cd bklv-frontend
npm install --silent
cd ..
echo "✅ Node.js dependencies installed"
echo ""

echo "======================================"
echo "Starting Services..."
echo "======================================"
echo ""

# Start Central Server
echo "🚀 Starting Central Server (port 9000)..."
cd bklv-backend
python3 server.py &
SERVER_PID=$!
cd ..
sleep 2
echo "✅ Central Server started (PID: $SERVER_PID)"
echo ""

# Start API Server
echo "🚀 Starting API Server (port 5500)..."
cd bklv-backend
python3 server_api.py &
API_PID=$!
cd ..
sleep 2
echo "✅ API Server started (PID: $API_PID)"
echo ""

# Start Client API Server
echo "🚀 Starting Client API Server (port 5501)..."
cd bklv-backend
python3 client_api.py &
CLIENT_API_PID=$!
cd ..
sleep 2
echo "✅ Client API Server started (PID: $CLIENT_API_PID)"
echo ""

# Start Frontend
echo "🚀 Starting Frontend (port 3000)..."
cd bklv-frontend
npm run electron:dev &
FRONTEND_PID=$!
cd ..
sleep 3
echo "✅ Frontend started (PID: $FRONTEND_PID)"
echo ""

echo "======================================"
echo "✅ All Services Running!"
echo "======================================"
echo ""
echo "📊 Admin Dashboard: http://localhost:3000 (choose Admin Dashboard)"
echo "👤 Client Interface: http://localhost:3000 (choose Client Interface)"
echo "🔌 API Server: http://localhost:5500"
echo "🔌 Client API: http://localhost:5501"
echo "🖥️  Central Server: Port 9000"
echo ""
echo "To stop all services, press Ctrl+C or run:"
echo "  kill $SERVER_PID $API_PID $CLIENT_API_PID $FRONTEND_PID"
echo ""
echo "PIDs saved to .pids file"
echo "$SERVER_PID $API_PID $CLIENT_API_PID $FRONTEND_PID" > .pids
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for user interrupt
trap "echo ''; echo '🛑 Stopping all services...'; kill $SERVER_PID $API_PID $CLIENT_API_PID $FRONTEND_PID 2>/dev/null; rm .pids; echo '✅ All services stopped'; exit 0" INT

wait
