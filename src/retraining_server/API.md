# Retraining Server API Documentation

## Overview
The retraining server provides endpoints to trigger model retraining and update the deployed model.

## Endpoints

### POST /retrain
- **Description:** Accepts new training data and triggers the retraining pipeline.
- **Request Body:**
  - New training data (format depends on implementation)
- **Response:**
  - Status message

### GET /status
- **Description:** Returns the status of the retraining process.
- **Response:**
  - Status message
