#!/bin/bash

echo ""
echo "==============================================="
echo "   Hospital Management System - Startup Script"
echo "==============================================="
echo ""

echo "Checking Python installation..."
if ! command -v python3 &> /dev/null
then
    echo "ERROR: Python3 is not installed"
    exit 1
fi

echo "Python found!"
echo ""

echo "Installing required packages..."
pip3 install -r requirements.txt

echo ""
echo "Starting Flask application..."
echo ""
echo "Application will be available at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 app.py
