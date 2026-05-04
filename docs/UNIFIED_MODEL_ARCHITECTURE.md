# Unified FT-Transformer — Architecture Diagrams

Visual companion to [`UNIFIED_MODEL.md`](UNIFIED_MODEL.md). Use this when you
need to *see* what the model does end-to-end. Numbers correspond to the
production tuned configuration:

| Hyperparam | Value | Meaning |
|---|---|---|
| `n_features` | 76 | CICFlowMeter flow features per sample |
| `n_classes` | 10 | Output classes (UNSW-NB15 schema) |
| `d_token` | 256 | Embedding dim per feature token |
| `n_blocks` | 3 | Transformer encoder layers stacked |
| `n_heads` | 8 | Attention heads per layer (head_dim = 32) |
| `ff_factor` | 2.0 | FFN hidden = `d_token * ff_factor = 512` |
| `dropout` | 0.0985 | Used inside attention + FFN |
| Total params | ~2.39M | (see §4) |

---

## 1. Top-level data flow

The model is a tabular Transformer: every numeric feature becomes its own
token, a [CLS] token is prepended, all tokens self-attend, and the [CLS]
output is classified.

```mermaid
flowchart TD
    A["Raw flow vector<br/>x ∈ R^(B × 76)<br/>76 CICFlowMeter features"]
    B["nan_to_num<br/>nan→0, inf→±1e9"]
    C["StandardScaler<br/>(fit on train only)"]
    D["Feature Tokenizer<br/>per-feature affine W_j, b_j<br/>76 features → 76 tokens of dim 256<br/>shape (B, 76, 256)"]
    E["Prepend [CLS] token<br/>learnable (1, 1, 256)<br/>→ shape (B, 77, 256)"]
    F["Transformer Encoder<br/>3 × (Pre-LN MHSA + Pre-LN FFN)"]
    G["Take CLS output<br/>z[:, 0] shape (B, 256)"]
    H["LayerNorm(256)"]
    I["Linear(256 → 10)<br/>classification head"]
    J["Logits<br/>(B, 10)"]
    K["softmax → probabilities<br/>argmax → class id"]

    A --> B --> C --> D --> E --> F --> G --> H --> I --> J --> K

    classDef io fill:#e8f4fd,stroke:#1976d2,color:#000;
    classDef proc fill:#fff8e1,stroke:#f9a825,color:#000;
    classDef out fill:#e8f5e9,stroke:#2e7d32,color:#000;
    class A,J io;
    class B,C,D,E,F,G,H,I proc;
    class K out;
```

The *only* part of the encoder output used by the classification head is
position 0 (the [CLS] token). All 76 feature tokens are present so they can
deposit information into [CLS] via attention; their final values are
discarded.

---

## 2. Feature Tokenizer

Each scalar feature `x_j` is independently projected to a 256-dim vector
via its own learned affine transformation:

```
token_j = x_j · W_j + b_j        with W_j, b_j ∈ R^256, j = 1..76
```

In code (broadcast over the batch):

```python
# tokenizer_w shape (76, 256), tokenizer_b shape (76, 256)
tokens = x.unsqueeze(-1) * self.tokenizer_w + self.tokenizer_b
# tokens shape: (B, 76, 256)
```

```mermaid
flowchart LR
    subgraph SI["Input scalars (B, 76)"]
        x1["x_1<br/>Flow Duration"]
        x2["x_2<br/>Total Fwd Pkts"]
        xj["…"]
        x76["x_76<br/>Idle Min"]
    end
    subgraph ST["Tokenizer params"]
        W["W ∈ R^(76 × 256)<br/>kaiming_uniform_"]
        B["b ∈ R^(76 × 256)<br/>zeros init"]
    end
    subgraph SO["Token output (B, 76, 256)"]
        t1["token_1 ∈ R^256"]
        t2["token_2 ∈ R^256"]
        tj["…"]
        t76["token_76 ∈ R^256"]
    end
    x1 -- "× W_1 + b_1" --> t1
    x2 -- "× W_2 + b_2" --> t2
    x76 -- "× W_76 + b_76" --> t76
    W -.-> SO
    B -.-> SO
```

**Why per-feature affine instead of shared embedding?** Each CICFlowMeter
feature has its own scale and statistical role (a flag count vs a packet
length vs an inter-arrival time). Giving each feature its own
`W_j, b_j` lets the model learn an embedding tailored to that feature's
distribution, instead of forcing 76 heterogeneous quantities through a
single shared linear layer.

---

## 3. Transformer encoder block (×3, Pre-LayerNorm)

After tokenization and CLS-prepend, the sequence has length 77 (76
features + CLS). Three identical encoder blocks process it. Each block is
Pre-LN: LayerNorm is applied *before* attention and FFN, and residuals are
added *after*.

```mermaid
flowchart TD
    IN["Input z<br/>(B, 77, 256)"]
    LN1["LayerNorm"]
    QKV["Linear(256 → 3·256)<br/>split into Q, K, V"]
    SPLIT["Split 8 heads<br/>head_dim = 32"]
    ATTN["Scaled Dot-Product Attention<br/>softmax(QKᵀ / √32) · V"]
    MERGE["Concat heads<br/>→ (B, 77, 256)"]
    OUT1["Linear out_proj<br/>(256 → 256)"]
    DROP1["Dropout p=0.0985"]
    ADD1[("⊕ residual")]
    LN2["LayerNorm"]
    FFN1["Linear(256 → 512)"]
    GELU["GELU"]
    FFN2["Linear(512 → 256)"]
    DROP2["Dropout p=0.0985"]
    ADD2[("⊕ residual")]
    OUT["Output z'<br/>(B, 77, 256)"]

    IN --> LN1 --> QKV --> SPLIT --> ATTN --> MERGE --> OUT1 --> DROP1 --> ADD1
    IN -.->|residual| ADD1
    ADD1 --> LN2 --> FFN1 --> GELU --> FFN2 --> DROP2 --> ADD2
    ADD1 -.->|residual| ADD2
    ADD2 --> OUT

    classDef attn fill:#fff3e0,stroke:#ef6c00,color:#000;
    classDef ffn fill:#e3f2fd,stroke:#1976d2,color:#000;
    classDef norm fill:#f3e5f5,stroke:#7b1fa2,color:#000;
    class LN1,LN2 norm;
    class QKV,SPLIT,ATTN,MERGE,OUT1,DROP1,ADD1 attn;
    class FFN1,GELU,FFN2,DROP2,ADD2 ffn;
```

### Multi-head attention math

For one head (of 8), with `head_dim = 32`:

```
Q, K, V = LayerNorm(z) · W_q,k,v     # each (B, 77, 32)
A       = softmax(Q · Kᵀ / √32)      # attention weights (B, 77, 77)
head    = A · V                      # (B, 77, 32)
```

The 8 heads run in parallel; their outputs are concatenated back to
`(B, 77, 256)` and projected once with `out_proj` (256→256).

The attention matrix `A` is 77×77, so every token (including CLS) attends
to every other token. This is the only place where features interact with
each other in the model — the FFN operates on each token independently.

### Pre-LN vs Post-LN

`norm_first=True` is set on `nn.TransformerEncoderLayer`. Pre-LN was chosen
because it gives more stable gradients early in training and matches the
Pre-LN variant used in Gorishniy 2021. With Post-LN the model often needs
warmup to avoid divergence; Pre-LN trains cleanly without it.

---

## 4. Parameter budget

```mermaid
pie title "Where the 2.39M parameters live"
    "Encoder MHA + FFN (×3)" : 2370
    "Tokenizer W + b (76×256×2)" : 39
    "Output head + final norm" : 3
    "[CLS] token" : 0.256
```

Per-component breakdown (approximate):

```
Tokenizer W       :   76 × 256                     =    19,456
Tokenizer b       :   76 × 256                     =    19,456
[CLS] token       :    1 × 1 × 256                 =       256
Encoder layer ×3  :  ≈790,000 each (attn ~263k + FFN ~263k + norms + biases)
                                                      ≈ 2,370,000
Final LayerNorm   :  256 × 2                       =       512
Head Linear       :  256 × 10 + 10                 =     2,570
                                                   ─────────────
Total             :                                ≈ 2,431,706
```

The encoder dominates. Most of *that* is the 8-head attention's QKV
projection (256 → 768 = 3·256) and the FFN's two linears (256 → 512 →
256), repeated 3 times.

---

## 5. From flow to alert (cnds runtime)

How the model fits into the cnds detection pipeline at inference time:

```mermaid
flowchart LR
    P["Scapy packet<br/>(captured on iface)"]
    D["Dispatcher<br/>flow tracking"]
    E["FlowRecord expires<br/>(timeout / idle / FIN)"]
    F["flow_extractor<br/>76 CICFlowMeter features"]
    G["FTTransformerEngine<br/>.predict(flow_vec)"]
    H["(label, confidence)<br/>e.g. ('DoS', 0.91)"]
    R["Other engines<br/>iforest, lstm, rules, baseline"]
    EN["EnsembleScorer<br/>weighted average"]
    AL["Alert persisted +<br/>websocket broadcast"]

    P --> D --> E --> F --> G --> H --> EN
    R --> EN --> AL

    classDef cap fill:#e8eaf6,stroke:#3949ab,color:#000;
    classDef ml fill:#fff3e0,stroke:#ef6c00,color:#000;
    classDef out fill:#e8f5e9,stroke:#2e7d32,color:#000;
    class P,D,E cap;
    class F,G,H,R,EN ml;
    class AL out;
```

The FT engine substitutes for the legacy `SupervisedEngine` (Random
Forest) in the cnds registry — same `is_available` /
`predict(flow_features)` / `anomaly_score(flow_features)` interface, so
the rest of the pipeline (ensemble, dedup, persistence, websocket) is
unchanged.

---

## 6. Where attention helps

The attention block is what makes FT-Transformer beat the gradient-boosted
baseline on minority classes. Concrete picture: if a flow has high
`SYN Flag Count` AND low `ACK Flag Count` AND high `Flow Packets/s`, those
three features individually look like normal short connections, but their
*combination* is a SYN-flood signature.

```mermaid
flowchart TB
    F1["Flow Packets/s<br/>= 18,000"]
    F2["SYN Flag Count<br/>= 18,000"]
    F3["ACK Flag Count<br/>= 0"]
    F4["Flow Duration<br/>= 0.0001s"]
    F5["… 72 other<br/>features"]

    CLS["[CLS] token<br/>(query)"]

    F1 --> CLS
    F2 --> CLS
    F3 --> CLS
    F4 --> CLS
    F5 --> CLS

    CLS --> H["High weight on F2 + F3 + F4<br/>encoded into [CLS]<br/>at the right attention layer"]
    H --> CLF["Classification head<br/>predicts class 3 = DoS"]

    classDef feat fill:#e1f5fe,stroke:#0277bd,color:#000;
    classDef cls fill:#ffeaa7,stroke:#fdcb6e,color:#000;
    class F1,F2,F3,F4,F5 feat;
    class CLS,H cls;
```

XGBoost handles this kind of interaction implicitly via tree splits, but
splits over the 76-feature space struggle when the discriminating
combination involves rare values. Attention lets the model weight any
subset of features simultaneously — the conditional structure is learned
end-to-end rather than encoded as a fixed split path.

---

## 7. References to source code

| Concept | File | Symbol |
|---|---|---|
| Class definition | [`cnds/src/models/ft_transformer.py`](../../cnds/src/models/ft_transformer.py) | `FTTransformer` |
| Optuna sweep | [`notebooks/ft_transformer_optuna_sweep.py`](../notebooks/ft_transformer_optuna_sweep.py) | `objective`, `class FTTransformer` |
| Inference engine | [`cnds/src/engines/ft_transformer_engine.py`](../../cnds/src/engines/ft_transformer_engine.py) | `FTTransformerEngine.predict` |
| Smoke test | [`cnds/scripts/smoke_test_ft_unified.py`](../../cnds/scripts/smoke_test_ft_unified.py) | `predict_batch` |
| Live runbook | [`cnds/doc/UNIFIED_FT_LIVE_RUNBOOK.md`](../../cnds/doc/UNIFIED_FT_LIVE_RUNBOOK.md) | (manual hping3/nmap) |
