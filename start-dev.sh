#!/bin/bash

# Script to run both Agent Zero backend and Next.js frontend

echo "Starting Agent Zero and VisuaLearn Frontend..."

# Function to cleanup background processes
cleanup() {
    echo "Stopping services..."
    kill $AGENT_ZERO_PID $NEXTJS_PID 2>/dev/null
    exit
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Start Agent Zero backend
echo "Starting Agent Zero backend..."
cd /workspaces/codespaces-blank/agent-zero
python run_ui.py &
AGENT_ZERO_PID=$!

# Wait a bit for Agent Zero to start
sleep 5

# Start Next.js frontend
echo "Starting Next.js frontend..."
cd /workspaces/codespaces-blank/agent-zero/main_ui
npm run dev &
NEXTJS_PID=$!

echo "Services started!"
echo "Agent Zero: http://localhost:50001"
echo "VisuaLearn Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for processes
wait $AGENT_ZERO_PID $NEXTJS_PID
