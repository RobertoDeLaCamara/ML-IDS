"""Build unified_supervised_training.ipynb programmatically.

Run: python build_unified_notebook.py
Output: unified_supervised_training.ipynb
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

def md(src):
    cells.append(nbf.v4.new_markdown_cell(src))

def code(src):
    cells.append(nbf.v4.new_code_cell(src))

md("""# Unified Supervised IDS Model — ML-IDS + cnds

**Goal**: train a single supervised model usable by both ML-IDS and cnds (cognitive-anomaly-detector / unified-ids), using the CICFlowMeter feature schema (75 features, CIC-IDS2017).

**Model**: FT-Transformer (Gorishniy et al., 2021) on PyTorch GPU (CUDA 12.8, Blackwell sm_120).
**Baseline**: XGBoost (GPU `hist`) for sanity comparison.

**Outputs** (in `../models/unified/`):
- `unified_ft_transformer.pt` — model weights + config
- `unified_xgboost.json` — XGBoost baseline
- `unified_scaler.pkl` — StandardScaler fitted on train
- `unified_metadata.json` — feature names, class mapping, metrics
""")

code("""# 1. Setup
import os, json, time, pickle, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, classification_report, confusion_matrix
from xgboost import XGBClassifier
import joblib

warnings.filterwarnings('ignore')

DATA_DIR = Path('/home/roberto/repos/ML-IDS/data/CIC-IDS2017')
OUT_DIR = Path('/home/roberto/repos/ML-IDS/models/unified')
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)

print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0))
""")

code("""# 2. Load + clean
t0 = time.time()
X_df = pd.read_csv(DATA_DIR / 'Data.csv')
y_df = pd.read_csv(DATA_DIR / 'Label.csv')
print(f'Loaded in {time.time()-t0:.1f}s. Shape: {X_df.shape}, {y_df.shape}')

FEATURE_NAMES = X_df.columns.tolist()
print(f'Features ({len(FEATURE_NAMES)}):', FEATURE_NAMES[:6], '...')

X = X_df.values.astype(np.float32)
y = y_df.values.ravel().astype(np.int64)

# Replace inf/-inf/nan (CICFlowMeter sometimes emits inf for div-by-zero)
n_inf = np.isinf(X).sum(); n_nan = np.isnan(X).sum()
X = np.nan_to_num(X, nan=0.0, posinf=1e9, neginf=-1e9)
print(f'Cleaned: {n_inf} inf and {n_nan} nan replaced.')

classes_unique, counts = np.unique(y, return_counts=True)
N_CLASSES = len(classes_unique)
print(f'\\nClasses: {N_CLASSES}')
for c, cnt in zip(classes_unique, counts):
    print(f'  class {c}: {cnt} ({100*cnt/len(y):.2f}%)')
""")

code("""# 3. Stratified split: 70/15/15
X_trainval, X_test, y_trainval, y_test = train_test_split(
    X, y, test_size=0.15, stratify=y, random_state=SEED
)
X_train, X_val, y_train, y_val = train_test_split(
    X_trainval, y_trainval, test_size=0.15/0.85, stratify=y_trainval, random_state=SEED
)
print(f'train {X_train.shape} | val {X_val.shape} | test {X_test.shape}')

# 4. Scale (fit only on train)
scaler = StandardScaler().fit(X_train)
X_train_s = scaler.transform(X_train).astype(np.float32)
X_val_s = scaler.transform(X_val).astype(np.float32)
X_test_s = scaler.transform(X_test).astype(np.float32)

joblib.dump(scaler, OUT_DIR / 'unified_scaler.pkl')
print('Scaler saved.')
""")

code("""# 5. XGBoost baseline (GPU hist)
print('Training XGBoost...')
t0 = time.time()
xgb = XGBClassifier(
    n_estimators=400,
    max_depth=8,
    learning_rate=0.1,
    tree_method='hist',
    device='cuda',
    objective='multi:softmax',
    num_class=N_CLASSES,
    eval_metric='mlogloss',
    early_stopping_rounds=20,
    random_state=SEED,
    n_jobs=-1,
)
xgb.fit(X_train_s, y_train, eval_set=[(X_val_s, y_val)], verbose=False)
xgb_train_time = time.time() - t0
print(f'XGBoost trained in {xgb_train_time:.1f}s, best_iteration={xgb.best_iteration}')

y_pred_xgb_test = xgb.predict(X_test_s)
xgb_f1_macro = f1_score(y_test, y_pred_xgb_test, average='macro')
xgb_f1_weighted = f1_score(y_test, y_pred_xgb_test, average='weighted')
print(f'XGBoost test F1 macro={xgb_f1_macro:.4f}  weighted={xgb_f1_weighted:.4f}')
print(classification_report(y_test, y_pred_xgb_test, digits=4, zero_division=0))

xgb.save_model(str(OUT_DIR / 'unified_xgboost.json'))
""")

code('''# 6. FT-Transformer model
class FTTransformer(nn.Module):
    """Self-contained FT-Transformer (Gorishniy 2021).
    All numerical features → tokenized via per-feature affine, prepended [CLS]
    token, processed through transformer encoder, [CLS] → classifier head.
    """
    def __init__(self, n_features, n_classes, d_token=128, n_blocks=3,
                 n_heads=8, ff_factor=2.0, dropout=0.1, attn_dropout=0.1):
        super().__init__()
        self.n_features = n_features
        self.d_token = d_token
        self.tokenizer_w = nn.Parameter(torch.empty(n_features, d_token))
        self.tokenizer_b = nn.Parameter(torch.zeros(n_features, d_token))
        nn.init.kaiming_uniform_(self.tokenizer_w, a=5**0.5)
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

    def forward(self, x):  # x: (B, F)
        tokens = x.unsqueeze(-1) * self.tokenizer_w + self.tokenizer_b  # (B, F, d)
        cls = self.cls.expand(x.size(0), -1, -1)
        z = torch.cat([cls, tokens], dim=1)  # (B, F+1, d)
        z = self.encoder(z)
        return self.head(self.norm(z[:, 0]))

CONFIG = dict(
    d_token=128, n_blocks=3, n_heads=8,
    ff_factor=2.0, dropout=0.1, attn_dropout=0.1,
    lr=3e-4, weight_decay=1e-5, batch_size=1024,
    max_epochs=50, patience=10, min_epochs=5,
)
print('Config:', CONFIG)
''')

code("""# 7. Train FT-Transformer
device = torch.device('cuda')
model = FTTransformer(
    n_features=X_train_s.shape[1], n_classes=N_CLASSES,
    d_token=CONFIG['d_token'], n_blocks=CONFIG['n_blocks'], n_heads=CONFIG['n_heads'],
    ff_factor=CONFIG['ff_factor'], dropout=CONFIG['dropout'], attn_dropout=CONFIG['attn_dropout'],
).to(device)
n_params = sum(p.numel() for p in model.parameters())
print(f'Model: {n_params/1e6:.2f}M params')

# Class weights for imbalance
w = (len(y_train) / (N_CLASSES * counts)).astype(np.float32)
class_weights = torch.tensor(w, device=device)
print('Class weights:', w)

train_ds = TensorDataset(torch.from_numpy(X_train_s), torch.from_numpy(y_train))
val_ds   = TensorDataset(torch.from_numpy(X_val_s),   torch.from_numpy(y_val))
train_dl = DataLoader(train_ds, batch_size=CONFIG['batch_size'], shuffle=True,
                      num_workers=2, pin_memory=True, drop_last=True)
val_dl   = DataLoader(val_ds,   batch_size=2048, shuffle=False,
                      num_workers=2, pin_memory=True)

opt = torch.optim.AdamW(model.parameters(), lr=CONFIG['lr'], weight_decay=CONFIG['weight_decay'])
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=CONFIG['max_epochs'])

best_f1 = -1.0; bad = 0
history = []
ckpt_path = OUT_DIR / 'unified_ft_transformer.pt'
t_start = time.time()

for epoch in range(CONFIG['max_epochs']):
    model.train(); t_ep = time.time(); train_loss = 0.0; n_seen = 0
    for xb, yb in train_dl:
        xb = xb.to(device, non_blocking=True); yb = yb.to(device, non_blocking=True)
        opt.zero_grad(set_to_none=True)
        with torch.amp.autocast('cuda', dtype=torch.bfloat16):
            logits = model(xb)
            loss = F.cross_entropy(logits, yb, weight=class_weights)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        train_loss += loss.item() * xb.size(0); n_seen += xb.size(0)
    sched.step()
    train_loss /= n_seen

    # Validate
    model.eval(); preds = []; tgts = []
    with torch.no_grad():
        for xb, yb in val_dl:
            xb = xb.to(device, non_blocking=True)
            with torch.amp.autocast('cuda', dtype=torch.bfloat16):
                logits = model(xb)
            preds.append(logits.argmax(1).cpu().numpy()); tgts.append(yb.numpy())
    preds = np.concatenate(preds); tgts = np.concatenate(tgts)
    f1m = f1_score(tgts, preds, average='macro')
    f1w = f1_score(tgts, preds, average='weighted')
    elapsed = time.time() - t_ep
    history.append({'epoch': epoch+1, 'train_loss': train_loss, 'val_f1_macro': f1m, 'val_f1_weighted': f1w, 'time_s': elapsed})
    print(f'ep {epoch+1:2d}  loss {train_loss:.4f}  val_f1_macro {f1m:.4f}  val_f1_w {f1w:.4f}  ({elapsed:.1f}s)')

    if f1m > best_f1:
        best_f1 = f1m; bad = 0
        torch.save({
            'state_dict': model.state_dict(),
            'config': CONFIG,
            'n_features': X_train_s.shape[1],
            'n_classes': N_CLASSES,
            'feature_names': FEATURE_NAMES,
            'epoch': epoch+1,
            'val_f1_macro': f1m,
        }, ckpt_path)
    else:
        bad += 1
        if bad >= CONFIG['patience'] and (epoch+1) >= CONFIG['min_epochs']:
            print(f'Early stop @ epoch {epoch+1} (best val_f1_macro={best_f1:.4f})')
            break

ft_train_time = time.time() - t_start
print(f'\\nFT-Transformer total training: {ft_train_time:.1f}s')
""")

code("""# 8. Test evaluation with best checkpoint
ckpt = torch.load(ckpt_path, weights_only=False)
model.load_state_dict(ckpt['state_dict']); model.eval()

test_ds = TensorDataset(torch.from_numpy(X_test_s), torch.from_numpy(y_test))
test_dl = DataLoader(test_ds, batch_size=2048, shuffle=False, num_workers=2, pin_memory=True)

ft_preds = []
with torch.no_grad():
    for xb, yb in test_dl:
        xb = xb.to(device, non_blocking=True)
        with torch.amp.autocast('cuda', dtype=torch.bfloat16):
            logits = model(xb)
        ft_preds.append(logits.argmax(1).cpu().numpy())
ft_preds = np.concatenate(ft_preds)

ft_f1_macro = f1_score(y_test, ft_preds, average='macro')
ft_f1_weighted = f1_score(y_test, ft_preds, average='weighted')

print('===== TEST SET RESULTS =====')
print(f'XGBoost:        F1 macro={xgb_f1_macro:.4f}  weighted={xgb_f1_weighted:.4f}  (train {xgb_train_time:.1f}s)')
print(f'FT-Transformer: F1 macro={ft_f1_macro:.4f}  weighted={ft_f1_weighted:.4f}  (train {ft_train_time:.1f}s, best ep={ckpt["epoch"]})')

print('\\n--- FT-Transformer per-class report ---')
print(classification_report(y_test, ft_preds, digits=4, zero_division=0))

print('--- Confusion matrix (rows=true, cols=pred) ---')
cm = confusion_matrix(y_test, ft_preds)
print(cm)
""")

code("""# 9. Persist metadata for inference
metadata = {
    'feature_names': FEATURE_NAMES,
    'n_features': len(FEATURE_NAMES),
    'n_classes': int(N_CLASSES),
    'class_counts_train': {int(c): int(cnt) for c, cnt in zip(*np.unique(y_train, return_counts=True))},
    'config': CONFIG,
    'metrics': {
        'xgboost': {
            'test_f1_macro': float(xgb_f1_macro),
            'test_f1_weighted': float(xgb_f1_weighted),
            'train_time_s': float(xgb_train_time),
        },
        'ft_transformer': {
            'test_f1_macro': float(ft_f1_macro),
            'test_f1_weighted': float(ft_f1_weighted),
            'train_time_s': float(ft_train_time),
            'best_epoch': int(ckpt['epoch']),
            'val_f1_macro_best': float(best_f1),
        },
    },
    'history': history,
    'split': {'train': len(y_train), 'val': len(y_val), 'test': len(y_test)},
    'data_source': str(DATA_DIR),
    'torch_version': torch.__version__,
    'gpu': torch.cuda.get_device_name(0),
}
with open(OUT_DIR / 'unified_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2, default=str)

print('\\nArtifacts:')
for p in sorted(OUT_DIR.iterdir()):
    print(f'  {p.name}  ({p.stat().st_size/1024:.1f} KB)')
""")

nb['cells'] = cells
nb['metadata'] = {
    'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
    'language_info': {'name': 'python', 'version': '3.12'},
}

out = '/home/roberto/repos/ML-IDS/notebooks/unified_supervised_training.ipynb'
with open(out, 'w') as f:
    nbf.write(nb, f)
print(f'Wrote {out}')
