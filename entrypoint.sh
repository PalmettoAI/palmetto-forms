#!/bin/sh
echo "=== ENV DEBUG ==="
env | grep -E 'PORT|RAILWAY' | sort
echo "=== STARTING ==="
python3 app.py
