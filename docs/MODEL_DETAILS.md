# Model Details

ML-IDS now serves a single unified supervised model — an Optuna-tuned
**FT-Transformer** trained jointly for ML-IDS and cnds. The legacy Random
Forest and Stacking classifiers remain in the codebase as sanity-check
baselines and are documented at the bottom of this page.

For the full architecture, training recipe, and inference contract see
[`UNIFIED_MODEL.md`](UNIFIED_MODEL.md). For the diagram-only companion see
[`UNIFIED_MODEL_ARCHITECTURE.md`](UNIFIED_MODEL_ARCHITECTURE.md).

## Production model — FT-Transformer (Optuna-tuned)

- **Algorithm:** FT-Transformer (Gorishniy et al., NeurIPS 2021) — per-feature
  affine tokenizer + 3 Pre-LayerNorm Transformer encoder blocks + linear head.
- **Parameters:** ~2.4M total.
- **Best hyperparameters** (Optuna sweep, 25 trials, TPESampler + MedianPruner):

```python
{'d_token': 256, 'n_blocks': 3, 'n_heads': 8, 'ff_factor': 2.0,
 'dropout': 0.0985, 'lr': 3.9e-4, 'weight_decay': 7.15e-5,
 'batch_size': 2048, 'class_weight': 'sqrt_inverse', 'use_focal': False}
```

- **Dataset:** CIC redistribution of UNSW-NB15 (~447k flows, 76 CICFlowMeter
  features, 10 classes — the dataset directory is named `CIC-IDS2017/` for
  historical reasons but the labels are UNSW-NB15).
- **Test metric:** F1 macro **0.6197** (XGBoost baseline 0.6095, default FT-T
  0.5446).
- **Class space:** `0=Benign, 1=Analysis, 2=Backdoor, 3=DoS, 4=Exploits,
  5=Fuzzers, 6=Generic, 7=Reconnaissance, 8=Shellcode, 9=Worms`.
- **Artifacts** (under `models/unified/`):
  - `unified_ft_transformer.pt` — model weights + config bundle.
  - `unified_scaler.pkl` — StandardScaler fitted on train.
  - `unified_metadata.json` — feature names, class counts, metrics history.
  - `unified_xgboost.json` — XGBoost baseline (sanity).
  - `ft_optuna_results.json` + `ft_optuna_study.pkl` — full sweep state.
- **MLflow registry:** `models:/ml-ids-unified-ft-transformer/<latest>`,
  artifact stored on MinIO under `s3://mlflow-artifacts/...`.

## Performance metrics

Reported on the held-out 15 % test split (67,188 rows):

| Metric | Value |
|---|---|
| F1 macro | 0.6197 |
| F1 weighted | ~0.93 |
| Accuracy | ~0.93 |

Per-class F1 (test split): Benign 0.99, Analysis 0.40, Backdoor 0.58, DoS
0.45, Exploits 0.77, Fuzzers 0.70, Generic 0.75, Reconnaissance 0.75,
Shellcode 0.35, Worms 0.46. Macro average is dominated by sample-size
noise on Worms (37 samples) and Analysis (58 samples).

## Inference

Use the helper class shipped with cnds:

```python
from src.models.ft_transformer import FTTransformer, build_from_checkpoint
import torch, joblib, numpy as np

scaler = joblib.load("models/unified/unified_scaler.pkl")
ckpt   = torch.load("models/unified/unified_ft_transformer.pt", map_location="cpu", weights_only=False)
model  = build_from_checkpoint(ckpt)        # FTTransformer with state_dict loaded
```

Or, in the cnds runtime, simply use `FTTransformerEngine.predict(flow_vec_76)`.
See [`UNIFIED_MODEL.md`](UNIFIED_MODEL.md) §4 for the raw inference snippet.

---

## Legacy baselines (sanity, not deployed)

These models remain in the notebooks for comparison. They are **not** used
by the inference server.

### Random Forest Classifier
- `n_estimators=100`, `max_depth=20`, `class_weight='balanced'` or custom weights.
- Used historically for initial classification and feature importance analysis.

### Stacking Classifier
- Base estimators: Random Forest, Logistic Regression.
- Meta-estimator: Logistic Regression.
- Wrapped in a pipeline with `StandardScaler`.
- Cross-validation: 5-fold.

### Performance reporting (legacy)
- Accuracy, precision, recall, F1-score (per class).
- Confusion matrix and ROC curves for each class.
- Feature importance (built-in and permutation-based).
