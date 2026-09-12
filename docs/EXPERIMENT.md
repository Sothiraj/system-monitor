# Experiment — Reproduction Guide

## 1. Environment

- Python 3.11, Linux.
- Dependencies (see `requirements.txt`): TensorFlow, scikit-learn,
  imbalanced-learn, pandas, numpy, matplotlib, seaborn, joblib, streamlit,
  fpdf2.

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 2. Dataset — NSL-KDD

| Split | Records |
|---|---|
| KDDTrain+ | 125,973 |
| KDDTest+ | 22,544 |

- 41 features per record: 3 symbolic (`protocol_type`, `service`, `flag`) and
  38 numeric.
- Preprocessing: one-hot encode the 3 symbolic features, min-max scale the 38
  numeric features → **122 features**.
- Labels: 5 categories (normal, DoS, Probe, R2L, U2R) and a 13-class granular
  split (normal + 12 attack families).

```bash
# download
git clone --depth 1 https://github.com/defcom17/NSL_KDD.git /tmp/NSL_KDD
cp /tmp/NSL_KDD/KDDTrain+.txt /tmp/NSL_KDD/KDDTest+.txt data/
```

> `train_all.py` runs this download automatically if the files are absent.

## 3. Train & evaluate

```bash
python code/train_all.py            # full run
python code/train_all.py --quick    # smoke run (fewer epochs)
```

This trains, for **both** the 5-class and 13-class tasks:

1. `RF (raw features)`
2. `MLP (deep baseline)`
3. `NDAE + RF` (base-paper re-implementation)
4. `CBAN-D` (ablation)
5. `CBAN` (proposed)

…and writes:

- `results/metrics_5class.json` / `.csv`
- `results/metrics_13class.json` / `.csv`
- `results/figures/fig1..fig7.png`
- `results/models/` — processor, encoder, RFs, attention weights (for the demo)

## 4. Reproduce the paper

```bash
python paper/generate_paper.py
```

produces `docs/paper/CBAN_IEEE_Paper.pdf` (rendered) and
`docs/paper/CBAN_IEEE_Paper.tex` (IEEEtran source, Overleaf-ready). The numbers
are read live from `results/*.json`.

## 5. Run the demo

```bash
streamlit run demo/app.py --server.address 0.0.0.0 --server.port 8501 \
  --server.headless true --server.enableCORS false --server.enableXsrfProtection false
```

## 6. Base-paper numbers (for comparison)

From Shone et al., IEEE TETCI 2(1):41–50, 2018 (NSL-KDD):

| Model | 5-class Acc. | R2L recall | U2R recall |
|---|---|---|---|
| DBN | 80.58 % | — | — |
| S-NDAE + RF | 85.42 % | 0.00 % | 0.00 % |
| S-NDAE + RF (13-class) | 89.22 % | — | — |

Note: the base paper evaluated a filtered test subset (18,794 records,
excluding novel attack families); this project uses the full 22,544-record
KDDTest+.

## 7. Hardware note

Training runs on CPU in this environment. TensorFlow logs a benign `cuInit`
warning when no GPU is present and continues on CPU.
