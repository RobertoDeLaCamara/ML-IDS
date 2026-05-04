"""Retroactively log the unified-model training to MLflow.

Reads the artifacts already produced in models/unified/ and logs:
- xgboost_baseline run (params, test metrics, .json model, scaler)
- ft_transformer_default run (params, test metrics, .pt artifact, scaler)
- optuna_sweep parent run with each trial as a nested child run
- ft_transformer_tuned run (best config, test metrics, .pt artifact, scaler)

All under experiment 'ml-ids-unified'.
"""
import json
from pathlib import Path

import joblib
import mlflow
import numpy as np
import torch

TRACKING_URI = 'http://192.168.1.147:5050'
EXPERIMENT = 'ml-ids-unified'

ROOT = Path('/home/roberto/repos/ML-IDS/models/unified')
META_PATH = ROOT / 'unified_metadata.json'
OPTUNA_PATH = ROOT / 'ft_optuna_results.json'
SCALER_PATH = ROOT / 'unified_scaler.pkl'
XGB_PATH = ROOT / 'unified_xgboost.json'
FT_PATH = ROOT / 'unified_ft_transformer.pt'
STUDY_PATH = ROOT / 'ft_optuna_study.pkl'

mlflow.set_tracking_uri(TRACKING_URI)
mlflow.set_experiment(EXPERIMENT)
print(f'tracking URI: {TRACKING_URI}')
print(f'experiment: {EXPERIMENT}')

# ---- Load artifacts ----
with open(META_PATH) as f:
    meta = json.load(f)
with open(OPTUNA_PATH) as f:
    optuna_meta = json.load(f)

# Common tags
common_tags = {
    'project': 'ml-ids',
    'task': 'unified-supervised-multiclass-ids',
    'dataset': 'CIC-IDS2017-prepared-447915',
    'feature_schema': 'CICFlowMeter-75',
    'n_classes': str(meta['n_classes']),
    'gpu': meta['gpu'],
    'torch_version': meta['torch_version'],
}

# ---- 1. XGBoost baseline ----
print('\n[1/4] Logging xgboost_baseline...')
with mlflow.start_run(run_name='xgboost_baseline') as run:
    mlflow.set_tags({**common_tags, 'model_family': 'gradient_boosting', 'model': 'xgboost'})
    mlflow.log_params({
        'n_estimators': 400,
        'max_depth': 8,
        'learning_rate': 0.1,
        'tree_method': 'hist',
        'device': 'cuda',
        'objective': 'multi:softmax',
        'eval_metric': 'mlogloss',
        'early_stopping_rounds': 20,
    })
    xgb_m = meta['metrics']['xgboost']
    mlflow.log_metrics({
        'test_f1_macro': xgb_m['test_f1_macro'],
        'test_f1_weighted': xgb_m['test_f1_weighted'],
        'train_time_s': xgb_m['train_time_s'],
    })
    mlflow.log_artifact(str(XGB_PATH), artifact_path='model')
    mlflow.log_artifact(str(SCALER_PATH), artifact_path='preprocessing')
    mlflow.log_artifact(str(META_PATH), artifact_path='metadata')
    print(f'  xgboost_baseline run_id: {run.info.run_id}')

# ---- 2. FT-Transformer default ----
print('\n[2/4] Logging ft_transformer_default...')
with mlflow.start_run(run_name='ft_transformer_default') as run:
    mlflow.set_tags({**common_tags, 'model_family': 'transformer', 'model': 'FT-Transformer',
                     'reference': 'Gorishniy 2021 (arXiv:2106.11959)', 'tuned': 'false'})
    mlflow.log_params(meta['config'])
    ft_m = meta['metrics']['ft_transformer']
    mlflow.log_metrics({
        'test_f1_macro': ft_m['test_f1_macro'],
        'test_f1_weighted': ft_m['test_f1_weighted'],
        'train_time_s': ft_m['train_time_s'],
        'best_epoch': ft_m['best_epoch'],
        'val_f1_macro_best': ft_m['val_f1_macro_best'],
    })
    for h in meta.get('history', []):
        mlflow.log_metric('val_f1_macro', h['val_f1_macro'], step=h['epoch'])
        mlflow.log_metric('val_f1_weighted', h['val_f1_weighted'], step=h['epoch'])
        mlflow.log_metric('train_loss', h['train_loss'], step=h['epoch'])
    mlflow.log_artifact(str(SCALER_PATH), artifact_path='preprocessing')
    mlflow.log_artifact(str(META_PATH), artifact_path='metadata')
    # NOTE: cannot log the default .pt: it was overwritten by the tuned retrain.
    print(f'  ft_default run_id: {run.info.run_id}')

# ---- 3. Optuna sweep (parent + children) ----
print('\n[3/4] Logging optuna_sweep...')
study = joblib.load(STUDY_PATH)
with mlflow.start_run(run_name='optuna_sweep') as parent:
    mlflow.set_tags({**common_tags, 'model_family': 'transformer', 'model': 'FT-Transformer',
                     'phase': 'hyperparameter_search', 'sampler': 'TPE-multivariate',
                     'pruner': 'MedianPruner'})
    mlflow.log_params({
        'n_trials_total': len(study.trials),
        'n_trials_complete': sum(1 for t in study.trials if t.state.name == 'COMPLETE'),
        'n_trials_pruned': sum(1 for t in study.trials if t.state.name == 'PRUNED'),
        'best_trial_number': study.best_trial.number,
    })
    mlflow.log_metric('best_val_f1_macro', study.best_value)
    mlflow.log_metric('sweep_total_time_min', optuna_meta['sweep_total_time_min'])
    mlflow.log_artifact(str(STUDY_PATH), artifact_path='optuna')
    mlflow.log_artifact(str(OPTUNA_PATH), artifact_path='optuna')
    parent_run_id = parent.info.run_id
    print(f'  parent run_id: {parent_run_id}')
    for t in study.trials:
        with mlflow.start_run(run_name=f'trial_{t.number}', nested=True):
            mlflow.set_tag('state', t.state.name)
            mlflow.log_params({k: v for k, v in t.params.items()})
            if t.value is not None:
                mlflow.log_metric('val_f1_macro', t.value)
            for k, v in (t.user_attrs or {}).items():
                if isinstance(v, (int, float)):
                    mlflow.log_metric(k, v)
            for step, val in (t.intermediate_values or {}).items():
                mlflow.log_metric('val_f1_macro_intermediate', val, step=step)
    print(f'  logged {len(study.trials)} nested trial runs')

# ---- 4. FT-Transformer tuned (the production artifact) ----
print('\n[4/4] Logging ft_transformer_tuned...')
ckpt = torch.load(FT_PATH, weights_only=False, map_location='cpu')
with mlflow.start_run(run_name='ft_transformer_tuned') as run:
    mlflow.set_tags({**common_tags, 'model_family': 'transformer', 'model': 'FT-Transformer',
                     'reference': 'Gorishniy 2021 (arXiv:2106.11959)',
                     'tuned': 'true', 'sweep_run_id': parent_run_id, 'production': 'candidate'})
    mlflow.log_params(optuna_meta['best_params'])
    mlflow.log_metrics({
        'test_f1_macro': optuna_meta['test_f1_macro'],
        'test_f1_weighted': optuna_meta['test_f1_weighted'],
        'val_f1_macro_sweep': optuna_meta['best_val_f1_macro'],
        'retrain_time_s': optuna_meta['retrain_time_s'],
        'retrain_best_epoch': optuna_meta['retrain_best_epoch'],
    })
    for h in optuna_meta.get('history_retrain', []):
        mlflow.log_metric('val_f1_macro', h['val_f1_macro'], step=h['epoch'])
        mlflow.log_metric('val_f1_weighted', h['val_f1_weighted'], step=h['epoch'])
    mlflow.log_artifact(str(FT_PATH), artifact_path='model')
    mlflow.log_artifact(str(SCALER_PATH), artifact_path='preprocessing')
    mlflow.log_artifact(str(OPTUNA_PATH), artifact_path='metadata')
    mlflow.log_artifact(str(META_PATH), artifact_path='metadata')
    tuned_run_id = run.info.run_id
    print(f'  ft_tuned run_id: {tuned_run_id}')

# Try to register the tuned model (best-effort: requires a configured registry)
try:
    model_uri = f'runs:/{tuned_run_id}/model/unified_ft_transformer.pt'
    mv = mlflow.register_model(model_uri=model_uri, name='ml-ids-unified-ft-transformer')
    print(f'\nRegistered as: {mv.name} version {mv.version}')
except Exception as e:
    print(f'\nModel registry skipped: {type(e).__name__}: {e}')

print('\nDone. Open the experiment at:')
print(f'  {TRACKING_URI}/#/experiments/{mlflow.get_experiment_by_name(EXPERIMENT).experiment_id}')
