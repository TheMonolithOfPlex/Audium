#!/bin/bash

# Exit on any error
set -e

# Load environment variables if using .env file (optional, for debugging/logging)
echo "Starting WhisperX..."

# Create necessary folders/files if they don’t exist
mkdir -p uploads logs static/transcripts

# Initialize uploads.json if missing
if [ ! -f uploads.json ]; then
  echo "[]" > uploads.json
  echo "Created uploads.json"
fi

# Run database migration or startup scripts here if needed
# echo "Running migrations..."

# Launch the Flask app
exec python3 web.py
