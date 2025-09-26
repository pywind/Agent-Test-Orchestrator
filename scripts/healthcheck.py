#!/usr/bin/env python3
"""Health check script for the Agent Test Orchestrator application."""

import sys
import httpx
import os

def check_health():
    """Check if the FastAPI application is healthy."""
    try:
        host = os.getenv('HOST', '0.0.0.0')
        port = os.getenv('PORT', '8000')
        url = f"http://{host}:{port}/health"
        
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url)
            
        if response.status_code == 200:
            print("Health check passed")
            return 0
        else:
            print(f"Health check failed with status: {response.status_code}")
            return 1
            
    except Exception as e:
        print(f"Health check failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_health())