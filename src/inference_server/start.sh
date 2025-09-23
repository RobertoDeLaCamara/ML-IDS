#!/bin/bash

cd /app/src/inference_server

# Start the inference server in the background
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Wait for the server to start
echo "Waiting for server to start..."
sleep 5

# Wait for the model to be initialized
echo "Waiting for model to be initialized..."
while true; do
    if python3 -c "import requests; r=requests.get('http://localhost:8000/health'); exit(0 if r.json().get('model_initialized') else 1)" 2>/dev/null; then
        echo "Model is initialized."
        break
    fi
    echo "Model not yet initialized, waiting 10 seconds..."
    sleep 10
done

# Start cicflowmeter
if [ "${START_CICFLOWMETER}" != "false" ]; then
    INTERFACE=${CIC_INTERFACE:-eth0}
    echo "Starting cicflowmeter on interface ${INTERFACE}..."
    /usr/local/bin/cicflowmeter -i ${INTERFACE} -u http://localhost:8000/predict
else
    echo "START_CICFLOWMETER is false, skipping cicflowmeter."
    # Keep the container running
    tail -f /dev/null
fi
