#!/bin/bash

# Validate deployment prerequisites
echo "🔍 Validating ML-IDS deployment prerequisites..."

# Check if interface exists on host
INTERFACE=${CIC_INTERFACE:-eth0}
echo "Checking interface: $INTERFACE"

if ip link show "$INTERFACE" >/dev/null 2>&1; then
    echo "✓ Interface '$INTERFACE' exists on host"
    
    # Check if interface is UP
    if ip link show "$INTERFACE" | grep -q "state UP"; then
        echo "✓ Interface '$INTERFACE' is UP"
    else
        echo "⚠️  Interface '$INTERFACE' is DOWN - consider bringing it up"
        echo "   Run: sudo ip link set $INTERFACE up"
    fi
else
    echo "❌ Interface '$INTERFACE' not found on host!"
    echo "Available interfaces:"
    ip link show | grep -E "^[0-9]+:" | cut -d: -f2 | tr -d ' '
    exit 1
fi

# Check Docker permissions
if ! docker ps >/dev/null 2>&1; then
    echo "❌ Docker not accessible - check permissions"
    exit 1
    exit 1
fi
echo "✓ Docker is accessible"

echo "✅ All prerequisites validated - ready to deploy!"