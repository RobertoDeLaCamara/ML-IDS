FROM python:3.13-slim-bookworm

WORKDIR /app

# Install cicflowmeter dependencies, jq, and curl
RUN apt-get update && apt-get install -y tcpdump jq curl iproute2 && rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir cicflowmeter
# Patch cicflowmeter bug (missing input_directory arg in main call)
RUN sed -i 's/args.output,/args.output, None,/g' /usr/local/lib/python3.13/site-packages/cicflowmeter/sniffer.py

# Make start.sh executable
RUN chmod +x src/inference_server/start.sh

EXPOSE 8000

CMD ["./src/inference_server/start.sh"]

