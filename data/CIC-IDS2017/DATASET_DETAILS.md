# CIC-IDS2017 Dataset Details

## Source
Canadian Institute for Cybersecurity

## Description
Realistic network traffic with labeled attacks and benign flows.

## Features
- Network flow statistics (e.g., duration, protocol, packet counts, byte counts)
- Extracted from raw network traffic using CICFlowMeter

## Labels
- Multi-class: e.g., BENIGN, DoS, DDoS, PortScan, Bot, BruteForce, Web Attack, etc.

## Preprocessing
- Feature selection and engineering performed in `notebooks/feature_engineering.ipynb`
- Data split and label encoding in `notebooks/model_training.ipynb`
