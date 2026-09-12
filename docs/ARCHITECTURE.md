# CBAN — Algorithm & Architecture

## Base paper (re-implemented)

Shone et al. (IEEE TETCI, 2018) stack **two non-symmetric deep auto-encoders
(NDAE)**, each with three hidden layers, and feed the bottleneck representation
into a **Random Forest**:

```
 input (41 → 122 after encoding) → NDAE1 → NDAE2 → embedding → Random Forest
```

Results reported on 5-class NSL-KDD: **85.42 %** accuracy vs. 80.58 % for DBN —
but **0 % recall on R2L and U2R**.

## Research gap

| Root cause | Consequence |
|---|---|
| Auto-encoder treats every feature equally | weak signals of rare attacks are diluted |
| cross-entropy objective | dominated by easy, frequent classes (DoS, Probe) |
| RF head sees imbalanced embeddings | cannot learn rare-class boundaries |

## CBAN (proposed)

```
                         ┌─────────────── focal loss −α_c (1−p_c)^γ log p_c
                         │                + inverse-frequency class weights
                         ▼
 x ∈ R^122 ──► Feature-Attention Gate ──► Dense 64 ──► Dense 32 ──► z ∈ R^16 ──► softmax → ŷ
              a = softmax(θ) ⊙ x          (ReLU+Dropout)                     │
                                                                              └─ saliency map
                                                                                 (interpretability)
```

### 1 · Feature-Attention Gate

A trainable vector `θ ∈ R^122` is normalized with softmax and applied
element-wise to the input:

```
a = softmax(θ) ⊙ x
```

- **Differentiable** → trained end-to-end with the rest of the encoder.
- **Interpretable** → after training, `softmax(θ)` is a per-feature saliency
  map used directly in the demo/paper (no SHAP/LIME needed).

### 3 · Balanced objective (focal loss + class weights)

```
L = −α_c (1 − p_c)^γ log p_c     (γ = 2, α_c = inverse class frequency)
```

The `(1 − p_c)^γ` factor down-weights *easy* examples (which the majority
classes mostly are) so the encoder spends its capacity on the *hard, rare*
examples. A softmax head over the 16-d embedding produces the final
distribution. Two ablations isolate each component: *CBAN w/o attention*
(plain encoder + focal + class weights) and *CBAN w/o focal* (attention +
class-weighted cross-entropy).

## Baselines (for comparison)

| Model | Description |
|---|---|
| `RF (raw features)` | 150-tree Random Forest on one-hot + scaled raw features |
| `MLP (deep baseline)` | dense 64→32 network with dropout, class-weighted CE |
| `NDAE + RF` | **re-implementation of the base paper** (stacked AE → RF) |
| `CBAN w/o focal` | ablation: attention + class-weighted CE (no focal loss) |
| `CBAN w/o attention` | ablation: plain encoder + focal + class weights |
| `CBAN` | full proposed model (attention + focal + class weights) |

## Training details

- Optimizer: Adam (lr = 1e-3), batch 1024, early stopping (patience 6).
- 10 % of the training split held out for validation, stratified.
- Random seed 42 everywhere → reproducible.
- Evaluation metrics: accuracy, macro/weighted precision, recall, F1, and
  **false-alarm rate** = FP / (FP + TN).
- Two tasks: **5-class** (normal/DoS/Probe/R2L/U2R) and **13-class**
  (normal + 12 attack families, mirroring the base paper's granular split).
