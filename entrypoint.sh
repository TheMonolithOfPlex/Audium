#!/bin/bash

# Exit on any error
set -e

# Load environment variables if using .env file (optional, for debugging/logging)
echo "Starting WhisperX..."

# Check write permissions for the current directory
if [ ! -w . ]; then
  echo "Error: No write permissions for the current directory." >&2
  exit 1
fi

if ! mkdir -p uploads logs static/transcripts; then
  echo "Error: Failed to create directories. Check permissions." >&2
  exit 1
fi

# Initialize uploads.json if missing
if [ ! -f uploads.json ]; then
  if echo "[]" > uploads.json 2>/dev/null; then
    echo "Created uploads.json"
  else
    echo "Error: Unable to create uploads.json. Check write permissions." >&2
    exit 1
  fi
fi

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
  echo "Error: python3 is not installed or not in PATH."
  exit 1
fi

# Check if Flask is installed
if ! python3 -c "import flask" &> /dev/null; then
  echo "Error: Flask is not installed. Install it using 'pip install flask'." >&2
  exit 1
fi

# Launch the Flask app
echo "Launching the Flask app..."
if ! exec python3 web.py; then
  echo "Error: Failed to launch the Flask app. Check for errors in web.py." >&2
  exit 1
fi
