#!/bin/bash

# Start the inference server in the background
# Run from /app so python sees src.inference_server as package
cd /app || { echo "Failed to change directory"; exit 1; }
export PYTHONPATH=$PYTHONPATH:/app
uvicorn src.inference_server.main:app --host 0.0.0.0 --port 8000 &

# Wait for the server to start
echo "Waiting for server to start..."
sleep 5

# Wait for the model to be initialized with timeout
echo "Waiting for model to be initialized..."
TIMEOUT=300
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -s http://localhost:8000/health | grep -q '"model_initialized":true'; then
        echo "Model is initialized."
        break
    fi
    echo "Model not yet initialized, waiting 10 seconds..."
    sleep 10
    ELAPSED=$((ELAPSED + 10))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "Timeout waiting for model initialization"
    exit 1
fi

# Start cicflowmeter
if [ "${START_CICFLOWMETER}" != "false" ]; then
    if [ -z "${CIC_INTERFACE}" ] || [ "${CIC_INTERFACE}" = "any" ] || [ "${CIC_INTERFACE}" = "auto" ]; then
        # Auto-detect interface with default route
        INTERFACE=$(ip -o -4 route show to default | awk '{print $5}' | head -n1)
        if [ -z "${INTERFACE}" ]; then
            # Fallback to first non-loopback
            INTERFACE=$(ip -o link show | awk -F': ' '!/lo/ {print $2}' | head -n1)
        fi
        echo "Auto-detected interface: ${INTERFACE}"
    else
        INTERFACE=${CIC_INTERFACE}
    fi
    
    # Validate interface exists
    if ! ip link show "${INTERFACE}" >/dev/null 2>&1; then
        echo "Error: Network interface '${INTERFACE}' not found"
        exit 1
    fi
    
    echo "Starting cicflowmeter on interface ${INTERFACE}..."
    /usr/local/bin/cicflowmeter -i "${INTERFACE}" -u http://localhost:8000/predict
else
    echo "START_CICFLOWMETER is false, skipping cicflowmeter."
    # Keep the container running
    tail -f /dev/null
fi
