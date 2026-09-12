"""
End-to-end experiment runner.

  1. Downloads/verifies NSL-KDD data.
  2. Preprocesses (one-hot + min-max) for the 5-class and 13-class tasks.
  3. Trains baselines + the proposed CBAN and its ablations.
  4. Evaluates on TWO test protocols:
       * filtered : test records whose attack family appears in training
                    (the base paper's 18,794-record protocol)
       * full     : all 22,544 KDDTest+ records (stricter, includes novel attacks)
  5. Persists metrics (JSON/CSV) and renders all paper/demo figures.
  6. Saves model artifacts used by the Streamlit demo.

Usage:  python code/train_all.py [--quick]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))

import make_figures as fig  # noqa: E402
from evaluate import evaluate, summarize_results  # noqa: E402
from models import (  # noqa: E402
    SEED,
    train_cban_deep,
    train_mlp,
    train_ndae,
    train_rf,
)
from preprocess import (  # noqa: E402
    download_data,
    known_attack_mask,
    load_preprocessed,
)

DATA_DIR = os.path.join(ROOT, "data")
MODEL_DIR = os.path.join(ROOT, "results", "models")
os.makedirs(MODEL_DIR, exist_ok=True)


def run_5class() -> dict:
    """Train + evaluate the 5-class models and ablations."""
    data, proc = load_preprocessed(
        os.path.join(DATA_DIR, "KDDTrain+.txt"),
        os.path.join(DATA_DIR, "KDDTest+.txt"),
        n_class=5,
    )
    X_tr, y_tr = data.X_train, data.y_train
    X_te, y_te = data.X_test, data.y_test
    mask = known_attack_mask(
        os.path.join(DATA_DIR, "KDDTrain+.txt"), os.path.join(DATA_DIR, "KDDTest+.txt")
    )
    X_te_f, y_te_f = X_te[mask], y_te[mask]
    cn = data.class_names

    results, times, models = {}, {}, {}

    def add(name, model, predict_fn, t):
        yhat_full = predict_fn(X_te)
        yhat_filt = predict_fn(X_te_f)
        results[name] = {
            "filtered": evaluate(y_te_f, yhat_filt, cn),
            "full": evaluate(y_te, yhat_full, cn),
        }
        times[name] = t
        models[name] = model

    # 1) Random Forest (shallow baseline)
    rf, t = train_rf(X_tr, y_tr, n_estimators=150)
    add("RF (raw features)", rf, lambda X: rf.predict(X), t)

    # 2) MLP (deep baseline: class-weighted CE)
    mlp, t = train_mlp(X_tr, y_tr, len(cn))
    add("MLP (deep baseline)", mlp, lambda X: np.argmax(mlp.predict(X, verbose=0), axis=1), t)

    # 3) NDAE + RF (base-paper re-implementation)
    ndae_encoder, t_ae = train_ndae(X_tr)
    Z_tr = ndae_encoder.predict(X_tr, verbose=0)
    rf_ndae, t_rf = train_rf(Z_tr, y_tr, n_estimators=200)
    add("NDAE + RF (Shone re-impl.)", (ndae_encoder, rf_ndae),
        lambda X: rf_ndae.predict(ndae_encoder.predict(X, verbose=0)), t_ae + t_rf)

    # 4) Ablation: CBAN without attention (focal + class weights, plain encoder)
    full_na, enc_na, t_na, _ = train_cban_deep(X_tr, y_tr, len(cn), use_attention=False)
    add("CBAN w/o attention", full_na,
        lambda X: np.argmax(full_na.predict(X, verbose=0), axis=1), t_na)

    # 5) Ablation: CBAN without focal loss (attention + class-weighted CE)
    full_nf, enc_nf, t_nf, _ = train_cban_deep(X_tr, y_tr, len(cn), use_focal=False)
    add("CBAN w/o focal", full_nf,
        lambda X: np.argmax(full_nf.predict(X, verbose=0), axis=1), t_nf)

    # 6) CBAN (proposed): attention + focal + class weights
    full, encoder, t_c, attn = train_cban_deep(X_tr, y_tr, len(cn))
    add("CBAN (proposed)", full,
        lambda X: np.argmax(full.predict(X, verbose=0), axis=1), t_c)

    return dict(results=results, times=times, data=data, proc=proc,
                encoder=encoder, full=full, attn=attn, class_names=cn,
                mask=mask, ndae=(ndae_encoder, rf_ndae))


def run_13class() -> dict:
    """Train + evaluate the 13-class models (RF, NDAE+RF, CBAN)."""
    data, proc = load_preprocessed(
        os.path.join(DATA_DIR, "KDDTrain+.txt"),
        os.path.join(DATA_DIR, "KDDTest+.txt"),
        n_class=13,
    )
    X_tr, y_tr = data.X_train, data.y_train
    X_te, y_te = data.X_test, data.y_test
    mask = known_attack_mask(
        os.path.join(DATA_DIR, "KDDTrain+.txt"), os.path.join(DATA_DIR, "KDDTest+.txt")
    )
    X_te_f, y_te_f = X_te[mask], y_te[mask]
    cn = data.class_names
    results, times, models = {}, {}, {}

    def add(name, model, predict_fn, t):
        results[name] = {
            "filtered": evaluate(y_te_f, predict_fn(X_te_f), cn),
            "full": evaluate(y_te, predict_fn(X_te), cn),
        }
        times[name] = t
        models[name] = model

    rf, t = train_rf(X_tr, y_tr, n_estimators=150)
    add("RF (raw features)", rf, lambda X: rf.predict(X), t)

    ndae_encoder, t_ae = train_ndae(X_tr)
    Z_tr = ndae_encoder.predict(X_tr, verbose=0)
    rf_ndae, t_rf = train_rf(Z_tr, y_tr, n_estimators=200)
    add("NDAE + RF (Shone re-impl.)", (ndae_encoder, rf_ndae),
        lambda X: rf_ndae.predict(ndae_encoder.predict(X, verbose=0)), t_ae + t_rf)

    full, encoder, t_c, attn = train_cban_deep(X_tr, y_tr, len(cn))
    add("CBAN (proposed)", full,
        lambda X: np.argmax(full.predict(X, verbose=0), axis=1), t_c)

    return dict(results=results, times=times, data=data, proc=proc,
                encoder=encoder, full=full, attn=attn, class_names=cn, mask=mask)


def dump_metrics(results: dict, name: str) -> None:
    """Flatten {model: {filtered: report, full: report}} into a JSON file."""
    flat = {}
    for model, d in results.items():
        for split in ("filtered", "full"):
            flat[f"{split}::{model}"] = d[split]
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", name), "w") as f:
        json.dump(flat, f, indent=2)
    print(f"[train] saved results/{name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smaller epochs for a fast smoke run")
    args = ap.parse_args()

    download_data(DATA_DIR)

    print("\n================= 5-CLASS =================")
    r5 = run_5class()
    dump_metrics(r5["results"], "metrics_5class.json")

    print("\n================= 13-CLASS ================")
    r13 = run_13class()
    dump_metrics(r13["results"], "metrics_13class.json")

    # ---- figures (headline = filtered protocol, secondary = full) ----
    cn5 = r5["class_names"]
    fig.architecture_diagram()
    fig.confusion_matrices(r5["results"], "NDAE + RF (Shone re-impl.)", "CBAN (proposed)",
                           cn5, split="filtered")
    fig.confusion_matrices(r5["results"], "NDAE + RF (Shone re-impl.)", "CBAN (proposed)",
                           cn5, split="full", name="fig2b_confusion_full.png")
    fig.per_class_f1(r5["results"], cn5, split="filtered")
    fig.per_class_f1(r5["results"], cn5, split="full", name="fig3b_per_class_f1_full.png")
    fig.attention_ranking(r5["attn"], r5["data"].feature_names)
    paper_refs = {
        "DBN (Shone et al.)": {"accuracy": 0.8058},
        "S-NDAE+RF (Shone et al.)": {"accuracy": 0.8542},
    }
    fig.overall_comparison(r5["results"], paper_refs, split="filtered")
    fig.training_time(r5["times"])
    fig.per_class_f1_13(r13["results"], r13["class_names"], split="filtered")

    # ---- demo artifacts (5-class) ----
    proc = r5["proc"]
    proc.save(os.path.join(MODEL_DIR, "processor.joblib"))
    r5["encoder"].save(os.path.join(MODEL_DIR, "cban_encoder.h5"))
    r5["full"].save(os.path.join(MODEL_DIR, "cban_full.h5"))
    import joblib
    joblib.dump(r5["ndae"][1], os.path.join(MODEL_DIR, "rf_ndae.joblib"))
    np.save(os.path.join(MODEL_DIR, "attn_weights.npy"), r5["attn"])
    meta = {
        "class_names": cn5,
        "feature_names": r5["data"].feature_names,
        "embed_dim": int(r5["encoder"].output_shape[-1]),
        "n_features": int(r5["data"].X_train.shape[1]),
        "n_filtered_test": int(r5["mask"].sum()),
        "n_full_test": int(len(r5["mask"])),
        "seed": SEED,
    }
    with open(os.path.join(MODEL_DIR, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    # ---- console summary ----
    for split, split_label in (("filtered", "paper protocol (18,794)"), ("full", "full KDDTest+ (22,544)")):
        print(f"\n========== 5-CLASS — {split_label} ==========")
        for m in ("NDAE + RF (Shone re-impl.)", "CBAN (proposed)", "MLP (deep baseline)",
                  "RF (raw features)", "CBAN w/o attention", "CBAN w/o focal"):
            rep = r5["results"][m][split]
            print(f"{m:28s} acc={rep['accuracy']*100:6.2f}%  F1(m)={rep['f1_macro']*100:6.2f}%  "
                  f"F1(w)={rep['f1_weighted']*100:6.2f}%  FAR={rep['false_alarm_rate']*100:6.2f}%  "
                  f"R2L={rep['per_class']['r2l']['recall']*100:6.2f}%  U2R={rep['per_class']['u2r']['recall']*100:6.2f}%")
    print("\n========== 13-CLASS ==========")
    for m, d in r13["results"].items():
        rep = d["filtered"]
        print(f"{m:28s} filt_acc={rep['accuracy']*100:6.2f}%  filt_F1(m)={rep['f1_macro']*100:6.2f}%  "
              f"full_acc={d['full']['accuracy']*100:6.2f}%")
    print("\nDone.")


if __name__ == "__main__":
    main()
