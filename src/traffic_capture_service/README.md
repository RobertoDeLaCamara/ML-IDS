# Rust Network Traffic Capture Service

A high-performance network traffic capture service written in Rust that captures network traffic, saves it as PCAP files, and uploads them to a MinIO server.

## Features
- Captures network traffic using libpcap
- Saves traffic to PCAP files with rotation based on size and time
- Uploads PCAP files to a MinIO server
- Runs in a Docker container with minimal resource usage
- Configurable via environment variables or config file

## Prerequisites
- Docker and Docker Compose
- libpcap development libraries (if building from source)

## Quick Start

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <repository-url>
   cd traffic_capture_service
   ```

2. Build and start the services:
   ```bash
   docker-compose up --build -d
   ```

3. Access the MinIO web interface at http://localhost:9001
   - Username: minioadmin
   - Password: minioadmin

## Configuration

Edit the `config.toml` file to customize the service:

```toml
# Network interface to capture traffic from
interface = "eth0"

# Directory to store PCAP files before uploading to MinIO
pcap_dir = "/data/pcaps"

# Duration in seconds before rotating to a new PCAP file
capture_duration_seconds = 300  # 5 minutes

# Maximum file size in MB before rotating to a new PCAP file
max_file_size_mb = 100  # 100 MB

# MinIO configuration
[minio]
endpoint = "minio:9000"
access_key = "minioadmin"
secret_key = "minioadmin"
bucket = "pcap-files"
use_ssl = false
```

## Environment Variables

You can override any configuration using environment variables with the `TRAFFIC_CAPTURE_` prefix. For example:

```bash
export TRAFFIC_CAPTURE_INTERFACE=eth0
export TRAFFIC_CAPTURE_PCAP_DIR=/data/pcaps
export TRAFFIC_CAPTURE_MINIO_ENDPOINT=minio:9000
```

## Building from Source

1. Install Rust and Cargo:
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

2. Install build dependencies:
   ```bash
   sudo apt-get update && sudo apt-get install -y libpcap-dev
   ```

3. Build the project:
   ```bash
   cargo build --release
   ```

4. Run the service:
   ```bash
   sudo ./target/release/traffic_capture_service
   ```

## Security Notes

- The service requires root privileges to capture network traffic
- Make sure to change the default MinIO credentials in production
- Consider enabling SSL/TLS for MinIO in production

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
