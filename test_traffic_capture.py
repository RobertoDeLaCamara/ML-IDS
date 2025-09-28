#!/usr/bin/env python3
import requests
import time
import subprocess

def generate_traffic():
    """Generate some network traffic"""
    print("Generating network traffic...")
    subprocess.run(['ping', '-c', '5', '8.8.8.8'], capture_output=True)
    requests.get('http://httpbin.org/get', timeout=5)

def check_logs():
    """Check if any predictions were logged"""
    try:
        with open('/var/log/ml-ids/positive_predictions.log', 'r') as f:
            content = f.read()
            if content:
                print("✓ Positive predictions found:")
                print(content[-500:])  # Last 500 chars
                return True
    except FileNotFoundError:
        pass
    
    try:
        with open('/var/log/ml-ids/negative_predictions.log', 'r') as f:
            content = f.read()
            if content:
                print("✓ Negative predictions found:")
                print(content[-500:])  # Last 500 chars
                return True
    except FileNotFoundError:
        pass
    
    print("❌ No prediction logs found")
    return False

if __name__ == "__main__":
    print("Testing CICFlowMeter traffic capture...")
    
    # Generate traffic
    generate_traffic()
    
    # Wait for processing
    print("Waiting 30 seconds for CICFlowMeter to process...")
    time.sleep(30)
    
    # Check logs
    check_logs()