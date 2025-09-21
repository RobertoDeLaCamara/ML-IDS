# Inference Server API Documentation

**OpenAPI Specification available:** [openapi.yaml](openapi.yaml)

## Overview

The inference server provides a REST API for making predictions with the trained ML model. The system is designed to integrate with CICFlowMeter, which automatically sends network flow features in real-time for analysis.

## CICFlowMeter Integration

CICFlowMeter runs automatically alongside the inference server and sends network flow features to the `/predict` endpoint in real-time. The system automatically maps CICFlowMeter features to the features expected by the ML model.

### Workflow

1. CICFlowMeter captures network packets from the specified interface
2. Extracts 78 statistical features from each flow
3. Sends features to the `/predict` endpoint via HTTP POST
4. The server maps features and performs prediction
5. Positive predictions (detected attacks) are logged

## Endpoints

### POST /predict
- **Description:** Returns predicted class labels for input features.
- **Usage:** Main endpoint for predictions, used by both CICFlowMeter and external clients.
- **Request Body:**
  ```json
  {
    "flow_duration": 1.234,
    "tot_fwd_pkts": 10,
    "tot_bwd_pkts": 8,
    "totlen_fwd_pkts": 1024,
    "totlen_bwd_pkts": 512,
    "fwd_pkt_len_max": 1500,
    "fwd_pkt_len_min": 64,
    "fwd_pkt_len_mean": 102.4,
    "fwd_pkt_len_std": 45.2,
    "bwd_pkt_len_max": 1000,
    "bwd_pkt_len_min": 32,
    "bwd_pkt_len_mean": 64.0,
    "bwd_pkt_len_std": 25.1,
    "flow_byts_s": 1024.5,
    "flow_pkts_s": 10.2,
    "flow_iat_mean": 0.1,
    "flow_iat_std": 0.05,
    "flow_iat_max": 0.5,
    "flow_iat_min": 0.01,
    "fwd_iat_tot": 0.8,
    "fwd_iat_mean": 0.08,
    "fwd_iat_std": 0.03,
    "fwd_iat_max": 0.2,
    "fwd_iat_min": 0.01,
    "bwd_iat_tot": 0.6,
    "bwd_iat_mean": 0.075,
    "bwd_iat_std": 0.02,
    "bwd_iat_max": 0.15,
    "bwd_iat_min": 0.01,
    "fwd_psh_flags": 0,
    "bwd_psh_flags": 0,
    "fwd_urg_flags": 0,
    "bwd_urg_flags": 0,
    "fwd_header_len": 20,
    "bwd_header_len": 20,
    "fwd_pkts_s": 5.1,
    "bwd_pkts_s": 4.0,
    "pkt_len_min": 32,
    "pkt_len_max": 1500,
    "pkt_len_mean": 83.2,
    "pkt_len_std": 35.1,
    "pkt_len_var": 1231.2,
    "fin_flag_cnt": 0,
    "syn_flag_cnt": 1,
    "rst_flag_cnt": 0,
    "psh_flag_cnt": 0,
    "ack_flag_cnt": 8,
    "urg_flag_cnt": 0,
    "cwr_flag_count": 0,
    "ece_flag_cnt": 0,
    "down_up_ratio": 0.5,
    "pkt_size_avg": 83.2,
    "fwd_seg_size_avg": 102.4,
    "bwd_seg_size_avg": 64.0,
    "fwd_byts_b_avg": 0.0,
    "fwd_pkts_b_avg": 0.0,
    "fwd_blk_rate_avg": 0.0,
    "bwd_byts_b_avg": 0.0,
    "bwd_pkts_b_avg": 0.0,
    "bwd_blk_rate_avg": 0.0,
    "subflow_fwd_pkts": 10,
    "subflow_fwd_byts": 1024,
    "subflow_bwd_pkts": 8,
    "subflow_bwd_byts": 512,
    "init_fwd_win_byts": 65535,
    "init_bwd_win_byts": 65535,
    "fwd_act_data_pkts": 8,
    "fwd_seg_size_min": 64,
    "active_mean": 0.1,
    "active_std": 0.05,
    "active_max": 0.3,
    "active_min": 0.01,
    "idle_mean": 0.2,
    "idle_std": 0.1,
    "idle_max": 0.5,
    "idle_min": 0.01
  }
  ```
- **Response:**
  ```json
  {
    "prediction": [0]
  }
  ```
- **Response Codes:**
  - `200`: Successful prediction
  - `400`: Invalid or missing features
  - `422`: Invalid data format
  - `503`: Model not available

### GET /health
- **Description:** Server health check endpoint.
- **Response:**
  ```json
  {
    "status": "healthy",
    "model_initialized": true
  }
  ```
- **Response Codes:**
  - `200`: Server running correctly

### GET /
- **Description:** Root endpoint with basic server information.
- **Response:**
  ```json
  {
    "message": "Inference server is running."
  }
  ```

## Feature Mapping

The system automatically maps CICFlowMeter features to the features expected by the ML model. The mapping includes 78 features covering:

- Flow statistics (duration, packets, bytes)
- Packet statistics (length, intervals)
- TCP flags (SYN, ACK, FIN, RST, etc.)
- Speed statistics (bytes/sec, packets/sec)
- Subflow statistics
- TCP window statistics
- Activity statistics

## Logging and Monitoring

- **Positive prediction logs**: Saved in `/app/logs/positive_predictions.log`
- **Application logs**: Available via `docker logs`
- **Health metrics**: Available via `/health` endpoint

## Configuration

The server is configured through environment variables:

- `MLFLOW_TRACKING_URI`: MLflow server URI
- `MLFLOW_S3_ENDPOINT_URL`: S3 endpoint for models
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: AWS credentials
- `CIC_INTERFACE`: Network interface for CICFlowMeter
- `LOG_DIR`: Directory for logs (default: `/app/logs`)
