# CBAN — Class-Balanced Attention Network for Network Intrusion Detection

An end-to-end research project that follows the standard academic pipeline:
**trending domain → base paper → research gap → novel algorithm →
implementation → comparison → IEEE paper → demo + documentation**.

| Step | Deliverable |
|------|-------------|
| 1 · Trending domain | **Cybersecurity** — ML/DL-based Network Intrusion Detection Systems (NIDS) |
| 2 · Base paper (IEEE Xplore) | Shone, Ngoc, Phai, Shi, *"A Deep Learning Approach to Network Intrusion Detection,"* **IEEE Trans. Emerging Topics in Computational Intelligence**, 2(1):41–50, 2018 — DOI [10.1109/TETCI.2017.2772792](https://doi.org/10.1109/TETCI.2017.2772792) |
| 3 · Research gap | Base model reports **0% recall on R2L & U2R** attack classes (NSL-KDD) — the rare-class detection gap |
| 4 · Novel algorithm | **CBAN** — feature-attention encoder + focal loss + class weights + targeted SMOTE + RF head |
| 5 · Implementation | Python (TensorFlow + scikit-learn) — `code/` |
| 6 · Comparison | RF, MLP, NDAE+RF (base re-implementation), CBAN-D, CBAN — `results/` |
| 7 · IEEE paper | `docs/paper/CBAN_IEEE_Paper.pdf` (+ IEEEtran `.tex`) |
| 8 · Demo + docs | Streamlit dashboard `demo/app.py`, this README, `docs/` |

---

## The problem

Deep-learning NIDS models learn features automatically, but their accuracy is
dominated by frequent traffic. The base paper's stacked **NDAE + Random Forest**
model reached **85.42 %** accuracy on 5-class NSL-KDD — yet **0 %** recall for the
**R2L** (remote-to-local) and **U2R** (user-to-root) attack families. Those are
exactly the attacks that signal a real compromise, so a detector that misses them
is not deployable.

## The proposed solution — CBAN

1. **Feature-Attention Gate** — a differentiable softmax mask `a = softmax(θ) ⊙ x`
   lets the encoder down-weight noisy features and up-weight discriminative ones.
   The trained gate *is* the explanation (built-in interpretability).
2. **Focal loss + class weights** — `L = −α_c (1 − p_c)^γ log p_c` focuses
   training on hard, rare examples instead of the easy majority classes.
3. **Softmax head** over the 16-d embedding, trained end-to-end.

> Combined, these address the root causes of the rare-class gap: equal feature
> treatment and a majority-dominated objective — plus they surface *why* a
> decision was made.

---

## Repository layout

```
system-monitor/
├── code/
│   ├── preprocess.py      # NSL-KDD parsing, one-hot + min-max, 5/13-class labels
│   ├── models.py          # RF, MLP, NDAE+RF, CBAN (FeatureAttention, focal loss, SMOTE)
│   ├── train_all.py       # end-to-end experiment runner
│   ├── evaluate.py        # accuracy / precision / recall / F1 / false-alarm rate
│   └── make_figures.py    # all paper + demo figures (PNG)
├── demo/
│   └── app.py             # Streamlit dashboard (live inference + explanation + results)
├── docs/
│   ├── paper/CBAN_IEEE_Paper.pdf   # IEEE-format paper (rendered)
│   ├── paper/CBAN_IEEE_Paper.tex   # IEEEtran source (Overleaf-ready)
│   ├── paper/generate_paper.py     # regenerates paper from results/*.json
│   ├── ARCHITECTURE.md             # algorithm details & formulas
│   ├── EXPERIMENT.md               # full reproduction steps
│   └── RESULTS.md                  # tables + analysis of the results
├── data/                  # KDDTrain+.txt / KDDTest+.txt (git-ignored)
└── results/               # metrics JSON/CSV, figures/, models/ (git-ignored)
```

## Quick start

```bash
# 1. environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. data (auto-downloaded by train_all.py, or manually)
git clone --depth 1 https://github.com/defcom17/NSL_KDD.git /tmp/NSL_KDD
cp /tmp/NSL_KDD/KDDTrain+.txt /tmp/NSL_KDD/KDDTest+.txt data/

# 3. train + evaluate + figures (5-class and 13-class)
python code/train_all.py

# 4. IEEE paper (PDF + TeX) from the results
python paper/generate_paper.py

# 5. demo dashboard
streamlit run demo/app.py
```

## Result highlights

The proposed CBAN improves **rare-class recall** (R2L/U2R) that the base model
scored **0 %** on, while raising macro-F1 and lowering the false-alarm rate.
Full numbers in [`docs/RESULTS.md`](docs/RESULTS.md) and
`results/metrics_5class.json`.

## Notes & limitations

- The base paper evaluated a *filtered* 18,794-record test subset (novel attack
  families removed). This project uses the **full 22,544-record KDDTest+** — a
  stricter, more honest setting.
- NSL-KDD is an aging benchmark (noted by the base authors themselves); it is
  used here to enable direct comparison. Future work: CIC-IDS-2017 / UNSW-NB15.
- Training runs on CPU in this environment (TensorFlow falls back to CPU).
