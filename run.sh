#!/bin/bash

# Load environment variables
if [ -f .env ]; then
  export $(cat .env | xargs)
fi

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --host $HOST --port $PORT --reload
