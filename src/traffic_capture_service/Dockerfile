# Build stage
FROM rust:1.86.0-slim as builder

WORKDIR /usr/src/traffic-capture
COPY . .

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

# Build the application
RUN cargo build --release

# Runtime stage
FROM debian:bullseye-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpcap0.8 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m appuser

# Create data directory
RUN mkdir -p /data/pcaps && \
    chown -R appuser:appuser /data

# Copy the binary and config
COPY --from=builder /usr/src/traffic-capture/target/release/traffic_capture_service /usr/local/bin/
COPY --from=builder /usr/src/traffic-capture/config.toml /etc/traffic-capture/

# Set the working directory
WORKDIR /data

# Run as non-root user
USER appuser

# Set environment variables
ENV RUST_LOG=info

# Run the application
CMD ["traffic_capture_service", "--config", "/etc/traffic-capture/config.toml"]
