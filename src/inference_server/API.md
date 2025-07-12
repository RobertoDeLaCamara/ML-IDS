# Inference Server API Documentation

**OpenAPI Specification available:** [openapi.yaml](openapi.yaml)

## Overview
The inference server provides a REST API for making predictions with the trained ML model.

## Endpoints

### POST /predict
- **Description:** Returns predicted class labels for input features.
- **Request Body:**
  ```json
  {
    "features": [
      [0.1, 0.2, ..., 0.5],
      [0.3, 0.4, ..., 0.7]
    ]
  }
  ```
- **Response:**
  ```json
  {
    "predictions": ["BENIGN", "DoS"]
  }
  ```

### GET /health
- **Description:** Health check endpoint.
- **Response:**
  ```json
  { "status": "ok" }
  ```
