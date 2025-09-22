FROM python:3.13-slim-bookworm

WORKDIR /app

# Install cicflowmeter dependencies, jq, and curl
RUN apt-get update && apt-get install -y tcpdump jq curl && rm -rf /var/lib/apt/lists/*

COPY . .

WORKDIR /app/src/inference_server

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir cicflowmeter

# Make start.sh executable
RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]

