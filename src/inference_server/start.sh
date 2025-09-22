#!/bin/bash

cd /app/src/inference_server

# Start the inference server in the background
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Wait for the model to be initialized
echo "Waiting for model to be initialized..."
while true; do
    if curl -s http://localhost:8000/health | jq -e '.model_initialized == true' > /dev/null 2>&1; then
        echo "Model is initialized."
        break
    fi
    echo "Model not yet initialized, waiting 10 seconds..."
    sleep 10
done

# Start cicflowmeter
INTERFACE=${CIC_INTERFACE:-eth0}
echo "Starting cicflowmeter on interface ${INTERFACE}..."
/usr/local/bin/cicflowmeter -i ${INTERFACE} -u http://localhost:8000/predict
