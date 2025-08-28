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

## Dataset Usage Conditions
This repository includes the CICIDS2017 dataset provided by the Canadian Institute for Cybersecurity (CIC) of the University of New Brunswick.
The dataset is intended for academic and research purposes only.
Use of the dataset is subject to the terms and conditions of the CIC. Citation of the original source is required when using this data.
Permission for public or commercial redistribution is not guaranteed. It is recommended to review the official conditions at:
https://www.unb.ca/cic/datasets/ids-2017.html
