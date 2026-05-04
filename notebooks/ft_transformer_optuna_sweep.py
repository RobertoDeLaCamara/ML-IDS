"""Optuna hyperparameter sweep for FT-Transformer on CIC-IDS2017.

Goal: see if FT-Transformer can match or beat XGBoost (test F1 macro 0.6095)
on the unified ML-IDS + cnds task.

Strategy:
- ~25 trials, TPESampler + MedianPruner.
- Max 30 epochs/trial with patience=5; pruning by val F1 macro after epoch 6.
- Search space covers architecture (d_token, n_blocks, n_heads, ff_factor),
  regularization (dropout, weight_decay), optimization (lr, batch_size),
  and the imbalance strategy (none / inverse / sqrt-inverse class weights, focal loss).
- After sweep: retrain the best config with full schedule and report on test.
"""
import json
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import optuna
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler
from sklearn.metrics import f1_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

warnings.filterwarnings('ignore')

DATA_DIR = Path('/home/roberto/repos/ML-IDS/data/CIC-IDS2017')
OUT_DIR = Path('/home/roberto/repos/ML-IDS/models/unified')
OUT_DIR.mkdir(parents=True, exist_ok=True)
SEED = 42
DEVICE = torch.device('cuda')

N_TRIALS = 25
MAX_EPOCHS = 30
PATIENCE = 5

# ---- Load data once ----
print('Loading data...')
t0 = time.time()
X_df = pd.read_csv(DATA_DIR / 'Data.csv')
y_df = pd.read_csv(DATA_DIR / 'Label.csv')
FEATURE_NAMES = X_df.columns.tolist()
X = np.nan_to_num(X_df.values.astype(np.float32), nan=0.0, posinf=1e9, neginf=-1e9)
y = y_df.values.ravel().astype(np.int64)
print(f'Loaded {X.shape} in {time.time()-t0:.1f}s')

X_trainval, X_test, y_trainval, y_test = train_test_split(
    X, y, test_size=0.15, stratify=y, random_state=SEED)
X_train, X_val, y_train, y_val = train_test_split(
    X_trainval, y_trainval, test_size=0.15/0.85, stratify=y_trainval, random_state=SEED)

scaler = StandardScaler().fit(X_train)
X_train_s = scaler.transform(X_train).astype(np.float32)
X_val_s = scaler.transform(X_val).astype(np.float32)
X_test_s = scaler.transform(X_test).astype(np.float32)

N_FEATURES = X_train_s.shape[1]
classes_unique, counts = np.unique(y_train, return_counts=True)
N_CLASSES = len(classes_unique)
print(f'features={N_FEATURES} classes={N_CLASSES} train={len(y_train)} val={len(y_val)} test={len(y_test)}')

# Pre-build tensor datasets reused across trials (saves I/O)
X_train_t = torch.from_numpy(X_train_s)
y_train_t = torch.from_numpy(y_train)
X_val_t = torch.from_numpy(X_val_s)
y_val_t = torch.from_numpy(y_val)
X_test_t = torch.from_numpy(X_test_s)
y_test_t = torch.from_numpy(y_test)


class FTTransformer(nn.Module):
    def __init__(self, n_features, n_classes, d_token, n_blocks, n_heads,
                 ff_factor, dropout):
        super().__init__()
        self.tokenizer_w = nn.Parameter(torch.empty(n_features, d_token))
        self.tokenizer_b = nn.Parameter(torch.zeros(n_features, d_token))
        nn.init.kaiming_uniform_(self.tokenizer_w, a=5 ** 0.5)
        self.cls = nn.Parameter(torch.empty(1, 1, d_token))
        nn.init.normal_(self.cls, std=0.02)
        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_token, nhead=n_heads,
            dim_feedforward=int(d_token * ff_factor),
            dropout=dropout, activation='gelu',
            batch_first=True, norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=n_blocks)
        self.norm = nn.LayerNorm(d_token)
        self.head = nn.Linear(d_token, n_classes)

    def forward(self, x):
        tokens = x.unsqueeze(-1) * self.tokenizer_w + self.tokenizer_b
        cls = self.cls.expand(x.size(0), -1, -1)
        z = torch.cat([cls, tokens], dim=1)
        z = self.encoder(z)
        return self.head(self.norm(z[:, 0]))


def make_class_weights(strategy):
    if strategy == 'none':
        return None
    if strategy == 'inverse':
        w = (len(y_train) / (N_CLASSES * counts)).astype(np.float32)
    elif strategy == 'sqrt_inverse':
        w = np.sqrt(len(y_train) / (N_CLASSES * counts)).astype(np.float32)
    else:
        raise ValueError(strategy)
    return torch.tensor(w, device=DEVICE)


def focal_loss(logits, targets, weight, gamma):
    logp = F.log_softmax(logits, dim=-1)
    p = logp.exp()
    ce = F.nll_loss(logp, targets, weight=weight, reduction='none')
    pt = p.gather(1, targets.unsqueeze(1)).squeeze(1)
    loss = ((1 - pt) ** gamma) * ce
    return loss.mean()


def objective(trial):
    cfg = {
        'd_token':       trial.suggest_categorical('d_token', [64, 128, 192, 256]),
        'n_blocks':      trial.suggest_int('n_blocks', 2, 5),
        'n_heads':       trial.suggest_categorical('n_heads', [4, 8]),
        'ff_factor':     trial.suggest_categorical('ff_factor', [1.0, 2.0, 4.0]),
        'dropout':       trial.suggest_float('dropout', 0.0, 0.3),
        'lr':            trial.suggest_float('lr', 1e-4, 1e-3, log=True),
        'weight_decay':  trial.suggest_float('weight_decay', 1e-6, 1e-3, log=True),
        'batch_size':    trial.suggest_categorical('batch_size', [512, 1024, 2048]),
        'class_weight':  trial.suggest_categorical('class_weight', ['none', 'inverse', 'sqrt_inverse']),
        'use_focal':     trial.suggest_categorical('use_focal', [False, True]),
    }
    if cfg['use_focal']:
        cfg['focal_gamma'] = trial.suggest_float('focal_gamma', 1.0, 3.0)
    # d_token must be divisible by n_heads
    if cfg['d_token'] % cfg['n_heads'] != 0:
        raise optuna.TrialPruned()

    torch.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)
    model = FTTransformer(N_FEATURES, N_CLASSES, cfg['d_token'], cfg['n_blocks'],
                          cfg['n_heads'], cfg['ff_factor'], cfg['dropout']).to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg['lr'], weight_decay=cfg['weight_decay'])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=MAX_EPOCHS)

    train_dl = DataLoader(TensorDataset(X_train_t, y_train_t),
                          batch_size=cfg['batch_size'], shuffle=True,
                          num_workers=2, pin_memory=True, drop_last=True)
    val_dl   = DataLoader(TensorDataset(X_val_t, y_val_t),
                          batch_size=4096, shuffle=False,
                          num_workers=2, pin_memory=True)

    cw = make_class_weights(cfg['class_weight'])
    best = -1.0; bad = 0
    t0 = time.time()
    for epoch in range(MAX_EPOCHS):
        model.train()
        for xb, yb in train_dl:
            xb = xb.to(DEVICE, non_blocking=True); yb = yb.to(DEVICE, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.amp.autocast('cuda', dtype=torch.bfloat16):
                logits = model(xb)
                if cfg['use_focal']:
                    loss = focal_loss(logits, yb, cw, cfg['focal_gamma'])
                else:
                    loss = F.cross_entropy(logits, yb, weight=cw)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        sched.step()

        model.eval(); preds = []; tgts = []
        with torch.no_grad():
            for xb, yb in val_dl:
                xb = xb.to(DEVICE, non_blocking=True)
                with torch.amp.autocast('cuda', dtype=torch.bfloat16):
                    logits = model(xb)
                preds.append(logits.argmax(1).cpu().numpy()); tgts.append(yb.numpy())
        f1m = f1_score(np.concatenate(tgts), np.concatenate(preds), average='macro')

        trial.report(f1m, epoch)
        if trial.should_prune():
            raise optuna.TrialPruned()
        if f1m > best:
            best = f1m; bad = 0
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    elapsed = time.time() - t0
    trial.set_user_attr('train_time_s', elapsed)
    trial.set_user_attr('epochs_run', epoch + 1)
    print(f'  trial {trial.number}: best_val_f1m={best:.4f} cfg={cfg} ({elapsed:.0f}s, ep={epoch+1})')
    return best


study = optuna.create_study(
    direction='maximize',
    sampler=TPESampler(seed=SEED, multivariate=True),
    pruner=MedianPruner(n_startup_trials=5, n_warmup_steps=6),
    study_name='ft_transformer_cic_ids2017',
)

print(f'\nStarting Optuna sweep: {N_TRIALS} trials, max {MAX_EPOCHS} epochs each')
study_t0 = time.time()
study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=False, gc_after_trial=True)
sweep_time = time.time() - study_t0

print('\n===== SWEEP COMPLETE =====')
print(f'Total sweep time: {sweep_time/60:.1f} min')
print(f'Best val F1 macro: {study.best_value:.4f}')
print(f'Best params: {study.best_params}')

# Save study
joblib.dump(study, OUT_DIR / 'ft_optuna_study.pkl')

# Top-5 trials summary
df = study.trials_dataframe(attrs=('number', 'value', 'state', 'user_attrs', 'params'))
top5 = df.dropna(subset=['value']).sort_values('value', ascending=False).head(5)
print('\nTop 5 trials:')
print(top5.to_string(index=False))

# ---- Retrain best on full schedule (50 epochs, patience 10) ----
print('\n===== RETRAIN BEST CONFIG (full schedule, 60 epochs) =====')
best_cfg = study.best_params.copy()

torch.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)
model = FTTransformer(N_FEATURES, N_CLASSES,
                      best_cfg['d_token'], best_cfg['n_blocks'],
                      best_cfg['n_heads'], best_cfg['ff_factor'],
                      best_cfg['dropout']).to(DEVICE)
opt = torch.optim.AdamW(model.parameters(), lr=best_cfg['lr'],
                        weight_decay=best_cfg['weight_decay'])
RETRAIN_EPOCHS = 60
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=RETRAIN_EPOCHS)
train_dl = DataLoader(TensorDataset(X_train_t, y_train_t),
                      batch_size=best_cfg['batch_size'], shuffle=True,
                      num_workers=2, pin_memory=True, drop_last=True)
val_dl = DataLoader(TensorDataset(X_val_t, y_val_t),
                    batch_size=4096, shuffle=False, num_workers=2, pin_memory=True)
cw = make_class_weights(best_cfg['class_weight'])
ckpt_path = OUT_DIR / 'unified_ft_transformer.pt'
best_f1 = -1.0; bad = 0; history = []
t_start = time.time()
for epoch in range(RETRAIN_EPOCHS):
    model.train()
    for xb, yb in train_dl:
        xb = xb.to(DEVICE, non_blocking=True); yb = yb.to(DEVICE, non_blocking=True)
        opt.zero_grad(set_to_none=True)
        with torch.amp.autocast('cuda', dtype=torch.bfloat16):
            logits = model(xb)
            if best_cfg.get('use_focal'):
                loss = focal_loss(logits, yb, cw, best_cfg['focal_gamma'])
            else:
                loss = F.cross_entropy(logits, yb, weight=cw)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
    sched.step()
    model.eval(); preds=[]; tgts=[]
    with torch.no_grad():
        for xb, yb in val_dl:
            xb = xb.to(DEVICE, non_blocking=True)
            with torch.amp.autocast('cuda', dtype=torch.bfloat16):
                logits = model(xb)
            preds.append(logits.argmax(1).cpu().numpy()); tgts.append(yb.numpy())
    f1m = f1_score(np.concatenate(tgts), np.concatenate(preds), average='macro')
    f1w = f1_score(np.concatenate(tgts), np.concatenate(preds), average='weighted')
    history.append({'epoch': epoch+1, 'val_f1_macro': f1m, 'val_f1_weighted': f1w})
    print(f'  ep {epoch+1:2d}  val_f1_macro {f1m:.4f}  val_f1_w {f1w:.4f}')
    if f1m > best_f1:
        best_f1 = f1m; bad = 0
        torch.save({
            'state_dict': model.state_dict(),
            'config': best_cfg,
            'n_features': N_FEATURES,
            'n_classes': N_CLASSES,
            'feature_names': FEATURE_NAMES,
            'epoch': epoch+1,
            'val_f1_macro': f1m,
        }, ckpt_path)
    else:
        bad += 1
        if bad >= 10:
            print(f'  early stop @ ep {epoch+1}')
            break
retrain_time = time.time() - t_start

# ---- Test eval ----
ckpt = torch.load(ckpt_path, weights_only=False)
model.load_state_dict(ckpt['state_dict']); model.eval()
test_dl = DataLoader(TensorDataset(X_test_t, y_test_t), batch_size=4096,
                     shuffle=False, num_workers=2, pin_memory=True)
preds = []
with torch.no_grad():
    for xb, yb in test_dl:
        xb = xb.to(DEVICE, non_blocking=True)
        with torch.amp.autocast('cuda', dtype=torch.bfloat16):
            logits = model(xb)
        preds.append(logits.argmax(1).cpu().numpy())
preds = np.concatenate(preds)
ft_f1_macro = f1_score(y_test, preds, average='macro')
ft_f1_weighted = f1_score(y_test, preds, average='weighted')

print('\n===== FINAL TEST RESULTS (TUNED FT-TRANSFORMER) =====')
print(f'XGBoost reference: F1 macro=0.6095  weighted=0.9373')
print(f'FT-T (default)   : F1 macro=0.5446  weighted=0.9158')
print(f'FT-T (tuned)     : F1 macro={ft_f1_macro:.4f}  weighted={ft_f1_weighted:.4f}  (retrain {retrain_time:.0f}s, best ep={ckpt["epoch"]})')
print('\nPer-class report:')
print(classification_report(y_test, preds, digits=4, zero_division=0))

# Update metadata
sweep_meta = {
    'best_params': best_cfg,
    'best_val_f1_macro': float(study.best_value),
    'sweep_total_trials': N_TRIALS,
    'sweep_total_time_min': sweep_time / 60,
    'retrain_time_s': retrain_time,
    'retrain_best_epoch': int(ckpt['epoch']),
    'test_f1_macro': float(ft_f1_macro),
    'test_f1_weighted': float(ft_f1_weighted),
    'top_5_trials': top5[['number', 'value', 'params_d_token', 'params_n_blocks',
                          'params_n_heads', 'params_lr', 'params_dropout']].to_dict('records')
                    if 'params_d_token' in top5.columns else top5.to_dict('records'),
    'history_retrain': history,
}
with open(OUT_DIR / 'ft_optuna_results.json', 'w') as f:
    json.dump(sweep_meta, f, indent=2, default=str)
print(f'\nSaved: {OUT_DIR/"ft_optuna_results.json"}')
print(f'Saved: {ckpt_path}')
