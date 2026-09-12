"""
Evaluation utilities: per-class and aggregate classification metrics,
false-alarm rate, confusion matrices, and result persistence.
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def false_alarm_rate(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Global false-alarm rate = FP / (FP + TN) over all classes.

    FP = sum of off-diagonal entries per class (predicted class i, true != i)
    TN = sum of all entries where neither the true nor predicted class is i.
    """
    cm = confusion_matrix(y_true, y_pred, labels=np.unique(np.r_[y_true, y_pred]))
    n = cm.shape[0]
    fp = tn = 0
    for i in range(n):
        fp += cm[:, i].sum() - cm[i, i]      # predicted i, actually not i
        mask = np.ones((n, n), dtype=bool)
        mask[i, :] = False
        mask[:, i] = False
        tn += cm[mask].sum()
    return float(fp) / float(fp + tn) if (fp + tn) > 0 else 0.0


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, class_names: list[str]) -> dict[str, Any]:
    """Full metric report for a multiclass prediction."""
    labels = list(range(len(class_names)))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    report = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)),
        "false_alarm_rate": false_alarm_rate(y_true, y_pred),
        "confusion_matrix": cm.tolist(),
        "per_class": {},
        "class_names": class_names,
    }
    for i, name in enumerate(class_names):
        report["per_class"][name] = {
            "precision": float(precision_score(y_true, y_pred, labels=[i], average=None, zero_division=0)[0]),
            "recall": float(recall_score(y_true, y_pred, labels=[i], average=None, zero_division=0)[0]),
            "f1": float(f1_score(y_true, y_pred, labels=[i], average=None, zero_division=0)[0]),
            "support": int(cm[i].sum()),
            "tp": int(cm[i, i]),
        }
    return report


def summarize_results(results: dict[str, dict[str, Any]], save_dir: str, filename: str) -> None:
    """Persist a results dict (model -> report) as JSON and a flat CSV."""
    os.makedirs(save_dir, exist_ok=True)
    json_path = os.path.join(save_dir, filename)
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    rows = []
    for model, rep in results.items():
        row = {
            "model": model,
            "accuracy": rep["accuracy"],
            "f1_macro": rep["f1_macro"],
            "f1_weighted": rep["f1_weighted"],
            "precision_macro": rep["precision_macro"],
            "recall_macro": rep["recall_macro"],
            "false_alarm_rate": rep["false_alarm_rate"],
        }
        for cname, c in rep["per_class"].items():
            row[f"{cname}_f1"] = c["f1"]
            row[f"{cname}_recall"] = c["recall"]
            row[f"{cname}_precision"] = c["precision"]
        rows.append(row)

    import pandas as pd

    pd.DataFrame(rows).to_csv(os.path.join(save_dir, filename.replace(".json", ".csv")), index=False)
    print(f"[evaluate] saved {json_path}")
