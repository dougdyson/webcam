#!/bin/bash

# Ollama Demo Launcher Script
# Runs the Ollama integration demo with proper setup

echo "🎬 Ollama Integration Demo Launcher"
echo "===================================="

# Check if we're in the right directory
if [ ! -f "examples/ollama_demo.py" ]; then
    echo "❌ Please run this script from the webcam project root directory"
    echo "   Current directory: $(pwd)"
    echo "   Expected to find: examples/ollama_demo.py"
    exit 1
fi

# Check if conda environment exists
if ! conda info --envs | grep -q "webcam"; then
    echo "❌ Conda environment 'webcam' not found"
    echo "   Please create it first: conda env create -f environment.yml"
    exit 1
fi

# Quick Ollama service check
echo "🔍 Checking Ollama service..."
if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo "✅ Ollama service is running"
else
    echo "⚠️  Ollama service doesn't appear to be running"
    echo "   Please start it: ollama serve"
    echo "   Then pull the model: ollama pull llama3.2-vision"
    echo ""
    echo "   Continue anyway? (y/n)"
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🚀 Starting demo..."
echo "   Press 'q' in the demo to quit"
echo "   Press 's' to take manual snapshot"  
echo "   Press 'd' to force description"
echo ""

# Activate conda environment and run demo
conda run -n webcam python examples/ollama_demo.py

echo ""
echo "👋 Demo finished!" 