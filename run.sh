#!/bin/bash
# Start the Cafe Management System
set -e
cd "$(dirname "$0")"
source venv/bin/activate
python app.py
