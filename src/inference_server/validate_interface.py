#!/usr/bin/env python3
import subprocess
import sys
import os

def check_interface_exists(interface_name):
    """Check if network interface exists"""
    try:
        result = subprocess.run(['ip', 'link', 'show', interface_name], 
                              capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    interface = os.getenv('CIC_INTERFACE', 'eth0')
    
    if not check_interface_exists(interface):
        print(f"ERROR: Network interface '{interface}' not found!")
        print("Available interfaces:")
        subprocess.run(['ip', 'link', 'show'])
        sys.exit(1)
    
    print(f"✓ Interface '{interface}' exists and is available")
    return True

if __name__ == "__main__":
    main()