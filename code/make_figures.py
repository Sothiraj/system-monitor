"""
Figure generation for the paper and the demo (matplotlib, headless).
All figures are saved to results/figures/ as PNG.

`results` has shape {model: {"filtered": report, "full": report}}.
"""

from __future__ import annotations

import os
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

FIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "figures")

CMAP = "YlOrRd"
COLORS = {
    "RF": "#9aa0a6",
    "MLP": "#6c8ebf",
    "NDAE": "#82b366",
    "CBAN": "#b85450",
}
MODEL_COLOR = {
    "RF (raw features)": "#9aa0a6",
    "MLP (deep baseline)": "#6c8ebf",
    "NDAE + RF (Shone re-impl.)": "#82b366",
    "CBAN w/o attention": "#d6b656",
    "CBAN w/o focal": "#c8a0e0",
    "CBAN (proposed)": "#b85450",
}


def _save(fig, name: str) -> str:
    os.makedirs(FIG_DIR, exist_ok=True)
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[figures] saved {path}")
    return path


# --------------------------------------------------------------------------
# Fig. 1 — architecture diagram
# --------------------------------------------------------------------------
def architecture_diagram() -> str:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")

    boxes = [
        (0.2, "Input\nx ∈ R^d\n(d = 122)", "#dae8fc"),
        (1.9, "Feature\nAttention Gate\na = softmax(θ) ⊙ x", "#ffe6cc"),
        (3.7, "Dense 64\nReLU + Dropout", "#dae8fc"),
        (5.3, "Dense 32\nReLU + Dropout", "#dae8fc"),
        (6.9, "Embedding\nz ∈ R^16", "#d5e8d4"),
        (8.3, "Softmax head\n(5 attack classes)", "#f8cecc"),
    ]
    y, h, w = 1.9, 1.2, 1.05
    for x, label, color in boxes:
        bb = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06",
                            linewidth=1.2, edgecolor="#444", facecolor=color)
        ax.add_patch(bb)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9)
    for x0 in (1.25, 3.0, 4.6, 6.2):
        ax.add_patch(FancyArrowPatch((x0, y + h / 2), (x0 + 0.62, y + h / 2),
                                     arrowstyle="-|>", mutation_scale=16, color="#444"))
    ax.text(5.0, 3.75, "Class-Balanced Attention Network (CBAN)",
            fontsize=13, weight="bold", ha="center")
    ax.text(5.0, 3.35, "trained end-to-end with focal loss L = −α_c (1−p_c)^γ log p_c  and class weights",
            fontsize=9.5, ha="center", color="#333")
    ax.text(7.5, 0.55, "interpretable: softmax(θ) = feature saliency", fontsize=9, ha="center", color="#555")
    return _save(fig, "fig1_architecture.png")


# --------------------------------------------------------------------------
# Fig. 2 — confusion matrices
# --------------------------------------------------------------------------
def confusion_matrices(results: dict[str, dict[str, Any]], left: str, right: str,
                       class_names: list[str], split: str = "filtered",
                       name: str = "fig2_confusion.png") -> str:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    for ax, model in zip(axes, (left, right)):
        cm = np.array(results[model][split]["confusion_matrix"], dtype=float)
        cm_norm = cm / cm.sum(axis=1, keepdims=True).clip(min=1e-9)
        im = ax.imshow(cm_norm, cmap=CMAP, vmin=0, vmax=1)
        ax.set_xticks(range(len(class_names)))
        ax.set_yticks(range(len(class_names)))
        ax.set_xticklabels([c.upper() for c in class_names], fontsize=8, rotation=45)
        ax.set_yticklabels([c.upper() for c in class_names], fontsize=8)
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, f"{cm[i, j]:.0f}", ha="center", va="center",
                        fontsize=6.5, color="black" if cm_norm[i, j] < 0.6 else "white")
        ax.set_title(model, fontsize=10, weight="bold")
    fig.colorbar(im, ax=axes, fraction=0.046, pad=0.04, label="row-normalized recall")
    fig.suptitle(f"NSL-KDD 5-class confusion matrices ({split} test set)", fontsize=12, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return _save(fig, name)


# --------------------------------------------------------------------------
# Fig. 3 — per-class F1
# --------------------------------------------------------------------------
def per_class_f1(results: dict[str, dict[str, Any]], class_names: list[str],
                 split: str = "filtered", name: str = "fig3_per_class_f1.png") -> str:
    models = list(results.keys())
    x = np.arange(len(class_names))
    n = len(models)
    width = 0.8 / n
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    for i, m in enumerate(models):
        f1 = [results[m][split]["per_class"][c]["f1"] for c in class_names]
        offs = (i - n / 2) * width + width / 2
        ax.bar(x + offs, f1, width, label=m, color=MODEL_COLOR.get(m, "#9aa0a6"))
    ax.set_xticks(x)
    ax.set_xticklabels([c.upper() for c in class_names])
    ax.set_ylabel("F1-score (%)")
    ax.set_ylim(0, 105)
    ax.legend(fontsize=7.5, ncol=2, loc="upper left")
    ax.axvspan(x[-2] - 0.5, x[-1] + 0.5, color="#f5f5f5", zorder=0)
    ax.text(x[-1] - 0.45, 102, "rare classes\n(R2L / U2R)", fontsize=8, color="#666")
    ax.set_title(f"Per-class F1-score — NSL-KDD 5-class ({split})", fontsize=12, weight="bold")
    fig.tight_layout()
    return _save(fig, name)


# --------------------------------------------------------------------------
# Fig. 4 — attention ranking
# --------------------------------------------------------------------------
def attention_ranking(attn: np.ndarray, feature_names: list[str],
                      name: str = "fig4_attention.png", top: int = 20) -> str:
    order = np.argsort(attn)[::-1][:top]
    vals = (attn[order] * 100)[::-1]
    labs = [feature_names[i] for i in order][::-1]
    fig, ax = plt.subplots(figsize=(8.2, 5.6))
    ax.barh(range(len(labs)), vals, color=COLORS["CBAN"])
    ax.set_yticks(range(len(labs)))
    ax.set_yticklabels(labs, fontsize=8)
    ax.set_xlabel("Attention weight (%)")
    ax.set_title("Top-20 features learned by the attention gate", fontsize=12, weight="bold")
    fig.tight_layout()
    return _save(fig, name)


# --------------------------------------------------------------------------
# Fig. 5 — overall accuracy vs paper baselines
# --------------------------------------------------------------------------
def overall_comparison(results: dict[str, dict[str, Any]], paper: dict[str, dict[str, float]],
                       split: str = "filtered", name: str = "fig5_overall.png") -> str:
    labels = list(paper.keys()) + list(results.keys())
    acc = [paper[m]["accuracy"] for m in paper] + [results[m][split]["accuracy"] for m in results]
    colors = ["#b0b0b0"] * len(paper) + [MODEL_COLOR.get(m, "#9aa0a6") for m in results]
    fig, ax = plt.subplots(figsize=(10.4, 4.6))
    bars = ax.bar(range(len(labels)), np.array(acc) * 100, color=colors)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Accuracy (%)")
    ax.set_ylim(0, 100)
    for b, v in zip(bars, acc):
        ax.text(b.get_x() + b.get_width() / 2, v * 100 + 1, f"{v*100:.2f}",
                ha="center", fontsize=7.5, weight="bold")
    ax.set_title(f"Accuracy vs. baselines — NSL-KDD 5-class ({split} test)", fontsize=12, weight="bold")
    fig.tight_layout()
    return _save(fig, name)


# --------------------------------------------------------------------------
# Fig. 6 — training time
# --------------------------------------------------------------------------
def training_time(times: dict[str, float], name: str = "fig6_time.png") -> str:
    labels = list(times.keys())
    vals = list(times.values())
    colors = [MODEL_COLOR.get(m, "#9aa0a6") for m in labels]
    fig, ax = plt.subplots(figsize=(9.4, 4.2))
    ax.bar(range(len(labels)), vals, color=colors)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=7.5)
    ax.set_ylabel("Wall-clock training time (s)")
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.02, f"{v:.1f}", ha="center", fontsize=7.5)
    ax.set_title("Training time on CPU (NSL-KDD train split)", fontsize=12, weight="bold")
    fig.tight_layout()
    return _save(fig, name)


# --------------------------------------------------------------------------
# Fig. 7 — 13-class per-class F1
# --------------------------------------------------------------------------
def per_class_f1_13(results: dict[str, dict[str, Any]], class_names: list[str],
                    split: str = "filtered", name: str = "fig7_13class_f1.png") -> str:
    models = [m for m in ("NDAE + RF (Shone re-impl.)", "CBAN (proposed)") if m in results]
    x = np.arange(len(class_names))
    fig, ax = plt.subplots(figsize=(11, 4.6))
    for i, m in enumerate(models):
        f1 = [results[m][split]["per_class"][c]["f1"] for c in class_names]
        ax.bar(x + (i - 0.5) * 0.4, f1, 0.4, label=m, color=MODEL_COLOR[m])
    ax.set_xticks(x)
    ax.set_xticklabels([c.upper() for c in class_names], rotation=45, ha="right", fontsize=7.5)
    ax.set_ylabel("F1-score (%)")
    ax.set_ylim(0, 105)
    ax.legend(fontsize=8)
    ax.set_title(f"Per-class F1-score — NSL-KDD 13-class ({split})", fontsize=12, weight="bold")
    fig.tight_layout()
    return _save(fig, name)
