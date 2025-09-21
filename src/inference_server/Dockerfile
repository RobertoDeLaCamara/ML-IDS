FROM python:3.13-slim-bookworm

WORKDIR /app

# Install cicflowmeter dependencies and jq
RUN apt-get update && apt-get install -y tcpdump jq && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir cicflowmeter

COPY . .

# Make start.sh executable
RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
