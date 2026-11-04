#!/usr/bin/env python3
"""Generate original EvidenceGuard-SOC report figures (4.2, 4.4, 4.5, 5.2).

All diagrams are newly drawn with matplotlib — no copyrighted web images
are copied. Outputs are report-ready PNG (300 dpi) + PDF (vector, for LaTeX).

Usage:
    pip install -r evidenceguard/requirements-figures.txt
    python evidenceguard/generate_figures.py --outdir evidenceguard/figures
    python evidenceguard/generate_figures.py --calibration evidenceguard/ccva_calibration_template.csv
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon
import networkx as nx

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)

BLUE = "#2F6FED"
BLUE_BG = "#EAF2FF"
BLUE_DARK = "#1F3A5F"
ORANGE = "#EF7D1A"
GREEN = "#1E9E5A"
GREEN_BG = "#E6F6EC"
RED = "#D64545"
RED_BG = "#FDECEC"
AMBER = "#B97A00"
AMBER_BG = "#FFF4DE"
PURPLE = "#8E5BD6"
GREY = "#5B6B7B"
GREY_BG = "#EFF2F5"
INK = "#1B2430"


# ---------------------------------------------------------------- utilities
def _box(ax, x, y, w, h, text, *, fontsize=7.8, fc=BLUE_BG, ec=BLUE,
         tc=INK, weight="normal", style="round,pad=0.04,rounding_size=0.12",
         lw=1.4, alpha=1.0, linespacing=1.35):
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle=style,
        facecolor=fc, edgecolor=ec, linewidth=lw, alpha=alpha,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2, y + h / 2, text, ha="center", va="center",
        fontsize=fontsize, color=tc, weight=weight, linespacing=linespacing,
        wrap=True,
    )
    return patch


def _arrow(ax, x1, y1, x2, y2, *, color="#334155", lw=1.5, dashed=False,
           rad=0.0, shrink=2.0, style="-|>"):
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style, mutation_scale=13,
        color=color, linewidth=lw,
        linestyle=(0, (4, 3)) if dashed else "solid",
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=0, shrinkB=shrink,
    )
    ax.add_patch(arrow)
    return arrow


def _step_dot(ax, x, y, n, *, r=0.13, fc=BLUE, tc="white", fontsize=8):
    c = plt.Circle((x, y), r, color=fc, ec="white", lw=1.2, zorder=5)
    ax.add_patch(c)
    ax.text(x, y, str(n), ha="center", va="center", fontsize=fontsize,
            weight="bold", color=tc, zorder=6)


# ------------------------------------------------------------- Figure 4.2
def fig4_2_preservation(out_png: Path, out_pdf: Path, dpi: int):
    fig, ax = plt.subplots(figsize=(12, 3.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.6)
    ax.axis("off")

    ax.text(6, 3.32, "Digital Evidence Preservation and Integrity Verification Workflow",
            ha="center", va="center", fontsize=11.5, weight="bold", color=INK)
    ax.text(6, 3.02, "The original exhibit is never analysed directly — only integrity-verified working copies are processed.",
            ha="center", va="center", fontsize=8, color=GREY, style="italic")

    y = 1.55
    h = 1.0
    boxes = [
        (0.20, 1.40, "Raw Evidence\nAcquisition", BLUE_BG, BLUE),
        (1.95, 1.60, "Write-Block &\nPreserve Original\n(read-only vault)", BLUE_BG, BLUE),
        (3.90, 1.30, "SHA-256 Hash\n(Hash A)", BLUE_BG, BLUE),
        (5.55, 1.50, "Create Forensic\nWorking Copy", BLUE_BG, BLUE),
    ]
    for i, (x, w, t, fc, ec) in enumerate(boxes, start=1):
        _box(ax, x, y, w, h, t, fc=fc, ec=ec, fontsize=7.6)
        _step_dot(ax, x + w / 2, y + h + 0.10, i)
        if i > 1:
            prev = boxes[i - 2]
            _arrow(ax, prev[0] + prev[1], y + h / 2, x, y + h / 2)

    # Decision diamond: re-hash & verify
    cx, cy = 8.05, y + h / 2
    hw, hh = 0.92, 0.68
    diamond = Polygon(
        [(cx - hw, cy), (cx, cy + hh), (cx + hw, cy), (cx, cy - hh)],
        closed=True, facecolor=AMBER_BG, edgecolor=AMBER, linewidth=1.6,
    )
    ax.add_patch(diamond)
    ax.text(cx, cy + 0.08, "Re-hash &\nVerify", ha="center", va="center",
            fontsize=7.6, weight="bold", color=INK, linespacing=1.3)
    ax.text(cx, cy - 0.32, "B == A ?", ha="center", va="center",
            fontsize=7.4, color=GREY, weight="bold",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#E3C97E", lw=1))
    _step_dot(ax, cx, cy + hh + 0.12, 5)
    _arrow(ax, 5.55 + 1.50, y + h / 2, cx - hw, cy)

    # Analyse box (Yes branch)
    ax_box_x, ax_box_w = 9.30, 1.45
    _box(ax, ax_box_x, y, ax_box_w, h, "Analyse\nWorking Copy\nOnly",
         fc=GREEN_BG, ec=GREEN, fontsize=7.8, weight="bold")
    _step_dot(ax, ax_box_x + ax_box_w / 2, y + h + 0.10, 6)
    _arrow(ax, cx + hw, cy, ax_box_x, y + h / 2)
    ax.text((cx + hw + ax_box_x) / 2, cy + 0.18, "Yes", fontsize=7.5,
            weight="bold", color=GREEN,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=GREEN, lw=0.9))

    # Quarantine box (No branch, below diamond)
    qx, qy, qw, qh = 7.28, 0.62, 1.55, 0.62
    _box(ax, qx, qy, qw, qh, "Quarantine &\nRe-acquire", fc=RED_BG, ec=RED,
         fontsize=7.4, weight="bold", tc="#7A1F1F")
    _arrow(ax, cx, cy - hh, cx, qy + qh, color=RED)
    ax.text(cx + 0.14, (cy - hh + qy + qh) / 2, "No", fontsize=7.5,
            weight="bold", color=RED, va="center",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=RED, lw=0.9))
    # loop back from quarantine to working-copy step
    _arrow(ax, qx, qy + qh / 2, 5.55 + 0.75, qy + qh / 2, color=RED,
           dashed=True, rad=0.0)
    _arrow(ax, 5.55 + 0.75, qy + qh / 2, 5.55 + 0.75, y, color=RED,
           dashed=True, rad=0.0)
    ax.text(6.05, 0.93, "retry", fontsize=7, color=RED, style="italic",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="#E8AFAF", lw=0.8))

    # Chain-of-custody banner
    _box(ax, 0.20, 0.06, 11.25, 0.38,
         "Chain-of-Custody Log  —  every acquisition, hash, verification and access is timestamped and hash-chained",
         fc=GREY_BG, ec="#B9C3CE", fontsize=7.4, tc="#334155", lw=1.1)
    for lx in (0.9, 2.75, 4.55, 6.3, 10.0):
        _arrow(ax, lx, 0.44, lx, 1.50, color="#9AA7B5", lw=1.0, dashed=True)

    fig.tight_layout()
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------- Figure 4.4
def _load_calibration(csv_path: Path | None):
    """Return (rows, synthetic_flag); rows are (conf, acc, count)."""
    default = [
        (0.05, 0.040, 120), (0.15, 0.130, 85), (0.25, 0.240, 90),
        (0.35, 0.330, 110), (0.45, 0.470, 150), (0.55, 0.530, 220),
        (0.65, 0.660, 310), (0.75, 0.730, 420), (0.85, 0.840, 680),
        (0.95, 0.930, 1150),
    ]
    if csv_path is None or not csv_path.exists():
        return default, True
    rows = []
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((
                float(r["predicted_confidence"]),
                float(r["observed_accuracy"]),
                int(r["count"]),
            ))
    if len(rows) != 10:
        raise ValueError(f"Expected 10 calibration bins, got {len(rows)} in {csv_path}")
    # Heuristic: numbers identical to the template are still a placeholder.
    synthetic = [tuple(x) for x in rows] == default
    return rows, synthetic


def fig4_4_reliability(out_png: Path, out_pdf: Path, dpi: int,
                       csv_path: Path | None):
    rows, synthetic = _load_calibration(csv_path)
    conf = [r[0] for r in rows]
    acc = [r[1] for r in rows]
    counts = [r[2] for r in rows]
    total = sum(counts)
    ece = sum(abs(a - c) * n / total for c, a, n in rows)
    mce = max(abs(a - c) for c, a, _ in rows)

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(8.6, 6.2), sharex=True,
        gridspec_kw={"height_ratios": [3.2, 1], "hspace": 0.06},
    )
    fig.suptitle("Reliability Diagram for Calibrated Cybersecurity Claim Verification",
                 fontsize=12, weight="bold", color=INK, y=0.98)
    fig.text(0.5, 0.93,
             "EvidenceGuard-SOC / CCVA — mean predicted confidence vs. observed claim accuracy (10 equal-width bins)",
             ha="center", fontsize=8.5, color=GREY, style="italic")

    w = 0.072
    ax1.bar(conf, acc, width=w, color=BLUE, edgecolor="white", linewidth=1.0,
            zorder=3)
    # Miscalibration gaps (red hatched)
    for c, a in zip(conf, acc):
        gap = abs(a - c)
        if gap < 1e-9:
            continue
        bottom = min(a, c)
        ax1.bar(c, gap, bottom=bottom, width=w, color="#F6B8B8",
                edgecolor="#C0392B", linewidth=1.0, hatch="///", zorder=4)
    ax1.plot([0, 1], [0, 1], color="black", linestyle="--", linewidth=1.3,
             zorder=5)
    # explicit legend (order: observed, gap, perfect)
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    obs_patch = Patch(facecolor=BLUE, edgecolor="white", label="Observed accuracy")
    gap_patch = Patch(facecolor="#F6B8B8", edgecolor="#C0392B", hatch="///",
                      label="Calibration gap |acc − conf|")
    perf_line = Line2D([0], [0], color="black", linestyle="--", linewidth=1.3,
                       label="Perfectly calibrated")
    ax1.legend(handles=[obs_patch, gap_patch, perf_line], fontsize=7.5,
               loc="upper left", framealpha=0.96, edgecolor="#C9D2DC")

    ax1.set_ylabel("Observed claim accuracy", fontsize=9.5)
    ax1.set_ylim(0, 1.03)
    ax1.set_xlim(0, 1)
    ax1.set_xticks([i / 10 for i in range(11)])
    ax1.set_yticks([i / 10 for i in range(0, 11, 2)])
    ax1.grid(axis="y", color="#E5EAF0", linewidth=0.8, zorder=0)
    ax1.set_axisbelow(True)

    # Stats box sits below the legend, in the empty space above the short bars.
    ax1.text(0.02, 0.66,
             f"ECE = {ece:.4f}\nMCE = {mce:.4f}\nN = {total:,} claims",
             transform=ax1.transAxes, va="top", ha="left", fontsize=8.5,
             color=INK, linespacing=1.5,
             bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="#C9D2DC", lw=1.1))

    if synthetic:
        # Centred in the empty middle-top area (clear of legend and tall bars).
        ax1.text(0.63, 0.97,
                 "PLACEHOLDER — replace with final CCVA split",
                 transform=ax1.transAxes, va="top", ha="center", fontsize=7.2,
                 weight="bold", color="#7A4A00",
                 bbox=dict(boxstyle="round,pad=0.35", fc="#FFF3D6", ec=AMBER, lw=1.1))

    ax2.bar(conf, counts, width=w, color="#9DB8E8", edgecolor=BLUE, linewidth=1.0)
    ax2.set_xlabel("Mean predicted confidence", fontsize=9.5)
    ax2.set_ylabel("Count", fontsize=9.5)
    ax2.set_xlim(0, 1)
    ax2.set_xticks([i / 10 for i in range(11)])
    ax2.grid(axis="y", color="#E5EAF0", linewidth=0.8, zorder=0)
    ax2.set_axisbelow(True)

    fig.subplots_adjust(hspace=0.06, top=0.88, bottom=0.09, left=0.09, right=0.98)
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    return ece, mce, total, synthetic


# ------------------------------------------------------------- Figure 4.5
def fig4_5_authorization(out_png: Path, out_pdf: Path, dpi: int):
    fig, ax = plt.subplots(figsize=(12, 6.0))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.2)
    ax.axis("off")

    ax.text(6, 5.95, "Risk-Constrained Response Authorization Architecture",
            ha="center", va="center", fontsize=11.5, weight="bold", color=INK)
    ax.text(6, 5.62, "Deny-by-default gating: only low-risk, evidence-backed actions are allowed — everything else is reviewed or denied.",
            ha="center", va="center", fontsize=8, color=GREY, style="italic")

    # Left: six attribute inputs (title + subtitle drawn separately)
    inputs = [
        ("Case Scope", "INC-2417 · windows-host"),
        ("Analyst Role", "Tier-2 · least-privilege"),
        ("Target Asset", "WS-214 · production"),
        ("Evidence Verdict", "CCVA: supported (0.87)"),
        ("Action Allow-list", "simulate-only by default"),
        ("Human Approval", "required if uncertain"),
    ]
    top, h, gap = 5.10, 0.52, 0.14
    in_x, in_w = 0.25, 2.55
    in_mid_ys = []
    for i, (title, sub) in enumerate(inputs):
        y = top - i * (h + gap) - h
        _box(ax, in_x, y, in_w, h, "", fc=BLUE_BG, ec=BLUE)
        ax.text(in_x + in_w / 2, y + h - 0.15, title, ha="center", va="center",
                fontsize=7.8, weight="bold", color=BLUE_DARK)
        ax.text(in_x + in_w / 2, y + h / 2 - 0.12, sub, ha="center", va="center",
                fontsize=7.4, color=INK)
        in_mid_ys.append(y + h / 2)

    ax.text(in_x + in_w / 2, top + 0.12, "CASE / ANALYST / EVIDENCE ATTRIBUTES",
            ha="center", va="bottom", fontsize=7.5, weight="bold", color=GREY)

    # Centre: policy decision engine
    eng_x, eng_w = 3.70, 3.60
    eng_bottom = top - 6 * (h + gap) + gap  # align with inputs block
    eng_h = top - eng_bottom
    eng = FancyBboxPatch(
        (eng_x, eng_bottom), eng_w, eng_h,
        boxstyle="round,pad=0.06,rounding_size=0.16",
        facecolor="#EFF4FF", edgecolor=BLUE_DARK, linewidth=1.8,
    )
    ax.add_patch(eng)
    ax.text(eng_x + eng_w / 2, top - 0.10, "POLICY DECISION ENGINE",
            ha="center", va="center", fontsize=9, weight="bold", color=BLUE_DARK)
    ax.text(eng_x + eng_w / 2, top - 0.32, "deny by default · all decisions logged",
            ha="center", va="center", fontsize=7.3, color=GREY, style="italic")

    # Stage boxes fill the engine interior (gaps computed, no dead space).
    stages = [
        ("1 · Policy Evaluation", "scope × role × asset × allow-list"),
        ("2 · Risk Constraints", "evidence-verdict gating"),
        ("3 · Human Approval", "escalation for uncertain cases"),
    ]
    header, pad = 0.55, 0.14
    sh = 0.80
    avail = eng_h - header - 2 * pad
    mid_gap = (avail - 3 * sh) / 2 if avail > 3 * sh else 0.14
    inner_top = top - header
    for j, (t, s) in enumerate(stages):
        sy = inner_top - pad - (j + 1) * sh - j * mid_gap
        _box(ax, eng_x + 0.22, sy, eng_w - 0.44, sh, "",
             fc="white", ec=BLUE, lw=1.2)
        ax.text(eng_x + eng_w / 2, sy + sh - 0.20, t, ha="center", va="center",
                fontsize=7.8, weight="bold", color=INK)
        ax.text(eng_x + eng_w / 2, sy + sh / 2 - 0.14, s, ha="center", va="center",
                fontsize=7.4, color=GREY)

    # input -> engine arrows (horizontal)
    for my in in_mid_ys:
        _arrow(ax, in_x + in_w, my, eng_x, my, color=BLUE, lw=1.3)

    # Right: three outcomes
    out_x, out_w = 8.20, 3.10
    outputs = [
        ("ALLOW FOR SIMULATION", "low risk + verified evidence", GREEN_BG, GREEN, "#0E6B3C"),
        ("REQUIRE REVIEW", "uncertain / elevated risk", AMBER_BG, AMBER, "#7A4A00"),
        ("DENY", "unsafe / unverified · logged rationale", RED_BG, RED, "#7A1F1F"),
    ]
    oh, ogap = 0.95, 0.30
    block_h = 3 * oh + 2 * ogap
    out_top = eng_bottom + eng_h / 2 + block_h / 2
    out_mid_ys = []
    for k, (t, s, fc, ec, tc) in enumerate(outputs):
        oy = out_top - (k + 1) * (oh + ogap) + ogap
        _box(ax, out_x, oy, out_w, oh, f"{t}\n{s}", fc=fc, ec=ec,
             fontsize=7.8, weight="bold", tc=tc, lw=1.6)
        out_mid_ys.append(oy + oh / 2)

    ax.text(out_x + out_w / 2, out_top + 0.12, "AUTHORIZATION OUTCOMES",
            ha="center", va="bottom", fontsize=7.5, weight="bold", color=GREY)

    eng_mid = eng_bottom + eng_h / 2
    for my in out_mid_ys:
        rad = 0.12 if my > eng_mid else (-0.12 if my < eng_mid else 0.0)
        _arrow(ax, eng_x + eng_w, eng_mid, out_x, my, color=BLUE_DARK,
               lw=1.5, rad=rad)

    # Bottom: audit banner (wide enough to catch the logging trunk)
    _box(ax, 0.25, 0.14, 11.45, 0.52,
         "Audit Log & Provenance Record  —  every decision, input snapshot and rationale is timestamped and hash-chained",
         fc=GREY_BG, ec="#B9C3CE", fontsize=8, tc="#334155", lw=1.2, weight="bold")
    _arrow(ax, eng_x + eng_w / 2, eng_bottom, eng_x + eng_w / 2, 0.66,
           color=GREY, lw=1.2, dashed=True)
    # Outcome logging via a trunk line right of the boxes (never through them).
    trunk_x = out_x + out_w + 0.22
    for my in out_mid_ys:
        _arrow(ax, out_x + out_w, my, trunk_x, my, color="#9AA7B5", lw=1.0)
    ax.plot([trunk_x, trunk_x], [0.9, max(out_mid_ys)], color="#9AA7B5",
            lw=1.0, linestyle=(0, (4, 3)))
    _arrow(ax, trunk_x, 0.9, trunk_x, 0.66, color="#9AA7B5", lw=1.0, dashed=True)
    ax.text(trunk_x + 0.05, (max(out_mid_ys) + 0.9) / 2, "logged",
            rotation=90, ha="center", va="center", fontsize=7, color=GREY,
            style="italic")

    fig.tight_layout()
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------- Figure 5.2
def fig5_2_graph(out_png: Path, out_pdf: Path, dpi: int):
    EP = "ENDPOINT\nWS-214"
    EXPLORER = "explorer.exe\nPID 4421"
    POWERSHELL = "powershell.exe\nPID 8872 ★"
    SVCHOST = "svchost.exe\nPID 1024"
    LNK = "invoice.pdf.lnk"
    BEACON = "beacon.ps1"
    OUT = "out.dat"
    C2 = "192.0.2.10:4444"
    UPDATE = "update.vendor.com"
    REG = "HKLM…\\Run"
    USER = "j.doe"

    edges = [
        (USER, EXPLORER, "logged on"),
        (EXPLORER, LNK, "opened"),
        (LNK, POWERSHELL, "spawned"),
        (POWERSHELL, BEACON, "executed"),
        (POWERSHELL, C2, "connected to"),
        (POWERSHELL, REG, "modified"),
        (POWERSHELL, OUT, "wrote"),
        (SVCHOST, UPDATE, "connected to"),
        (EP, EXPLORER, "hosted"),
        (EP, POWERSHELL, "hosted"),
        (EP, SVCHOST, "hosted"),
    ]

    pos = {
        EP: (0.0, 0.45),
        USER: (-3.2, 1.6),
        EXPLORER: (-1.6, 1.0),
        LNK: (-2.3, -0.7),
        POWERSHELL: (0.2, -0.95),
        BEACON: (1.9, -1.7),
        C2: (2.7, -0.5),
        OUT: (1.9, 0.35),
        REG: (0.9, -2.3),
        SVCHOST: (-0.1, 1.7),
        UPDATE: (2.1, 1.8),
    }

    # Approx. node boundary distance from centre (for arrow trimming / labels).
    RADII = {
        EP: 0.60, USER: 0.45, EXPLORER: 0.56, POWERSHELL: 0.63,
        SVCHOST: 0.56, LNK: 0.51, BEACON: 0.51, OUT: 0.41,
        C2: 0.88, UPDATE: 0.88, REG: 0.48,
    }

    fig, ax = plt.subplots(figsize=(11.5, 6.6))
    ax.set_xlim(-4.2, 3.9)
    ax.set_ylim(-3.2, 2.7)
    ax.axis("off")
    ax.text(-0.15, 2.55, "Endpoint Process Relationship Graph — illustrative example",
            ha="center", va="center", fontsize=11.5, weight="bold", color=INK)
    ax.text(-0.15, 2.30, "Node colours encode entity type; edge labels encode the observed relationship.",
            ha="center", va="center", fontsize=8, color=GREY, style="italic")

    def _trimmed(u, v):
        """Arrow geometry: from source centre to just outside target boundary."""
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist
        gap = RADII[v] + 0.07
        ex, ey = x2 - ux * gap, y2 - uy * gap
        # visible-segment midpoint (for labels), clear of both nodes
        sx, sy = x1 + ux * RADII[u] * 0.9, y1 + uy * RADII[u] * 0.9
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        return (x1, y1, ex, ey, mx, my, -uy, ux)

    # edges (tails hide under source nodes; heads stop outside targets)
    for u, v, _lbl in edges:
        x1, y1, ex, ey, *_ = _trimmed(u, v)
        hostile = v in (C2, BEACON, REG) or u == POWERSHELL
        _arrow(ax, x1, y1, ex, ey,
               color="#B03A3A" if hostile else "#5B6B7B",
               lw=1.6 if hostile else 1.3, rad=0.0, shrink=1.0)

    # edge labels sit beside the visible segment, not on nodes
    NUDGE = {
        (EP, SVCHOST): (0.30, 0.02),
        (EP, POWERSHELL): (0.30, 0.0),
        (EP, EXPLORER): (0.0, 0.16),
        (POWERSHELL, REG): (0.34, 0.02),
    }
    for u, v, lbl in edges:
        *_, mx, my, px, py = _trimmed(u, v)
        nx_, ny_ = NUDGE.get((u, v), (px * 0.16, py * 0.16))
        ax.text(mx + nx_, my + ny_, lbl, ha="center", va="center", fontsize=6.8,
                color="#334155", zorder=6,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#C9D2DC",
                          lw=0.7, alpha=0.97))

    def node(xy, text, *, fc, ec="white", tc="white", size=0.62, shape="circle",
             lw=2.0, fontsize=7.4, weight="bold"):
        x, y = xy
        if shape == "square":
            patch = FancyBboxPatch((x - size * 0.74, y - size / 2), size * 1.48,
                                   size, boxstyle="round,pad=0.02,rounding_size=0.10",
                                   facecolor=fc, edgecolor=ec, linewidth=lw)
        elif shape == "diamond":
            patch = Polygon([(x, y + size / 1.7), (x + size / 1.05, y),
                             (x, y - size / 1.7), (x - size / 1.05, y)],
                            closed=True, facecolor=fc, edgecolor=ec, linewidth=lw)
        else:
            patch = plt.Circle((x, y), size / 1.55, color=fc, ec=ec, lw=lw)
        ax.add_patch(patch)
        ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
                weight=weight, color=tc, linespacing=1.25)

    node(pos[EP], EP, fc=BLUE, size=0.85, shape="square", fontsize=8)
    node(pos[USER], f"user\n{USER}", fc="#6B7684", size=0.66)
    node(pos[EXPLORER], EXPLORER, fc=ORANGE, size=0.84, fontsize=7.2)
    node(pos[POWERSHELL], POWERSHELL, fc="#C0392B", ec="#7A1F1F", size=0.94,
         fontsize=7.2, lw=2.6)
    node(pos[SVCHOST], SVCHOST, fc=ORANGE, size=0.84, fontsize=7.2)
    node(pos[LNK], LNK, fc="#2EAB66", size=0.76, fontsize=7.2)
    node(pos[BEACON], BEACON, fc="#2EAB66", ec="#C0392B", size=0.76,
         fontsize=7.4, lw=2.4)
    node(pos[OUT], OUT, fc="#2EAB66", size=0.60)
    node(pos[C2], C2, fc=RED, ec="#7A1F1F", size=0.88, shape="diamond",
         fontsize=7.0, lw=2.4)
    node(pos[UPDATE], UPDATE, fc="#7FB6D9", tc=INK, size=0.88,
         shape="diamond", fontsize=6.8)
    node(pos[REG], REG, fc=PURPLE, size=0.72, fontsize=7.2)

    # legend outside the axes (right) so it never covers a node
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=BLUE, edgecolor=BLUE, label="Endpoint"),
        Patch(facecolor=ORANGE, edgecolor=ORANGE, label="Process"),
        Patch(facecolor="#C0392B", edgecolor="#7A1F1F", label="Suspicious process"),
        Patch(facecolor="#2EAB66", edgecolor="#2EAB66", label="File"),
        Patch(facecolor=RED, edgecolor=RED, label="Network (external)"),
        Patch(facecolor=PURPLE, edgecolor=PURPLE, label="Registry"),
        Patch(facecolor="#6B7684", edgecolor="#6B7684", label="User"),
    ]
    leg = ax.legend(handles=handles, fontsize=7.2, loc="upper left",
                    bbox_to_anchor=(1.005, 0.99), framealpha=0.97,
                    edgecolor="#C9D2DC", title="Entity types", title_fontsize=7.5)
    leg.get_title().set_weight("bold")

    ax.text(-0.15, -3.0,
            "Illustrative subgraph — shows node/edge types only, not the complete EvidenceGuard-SOC graph schema.",
            ha="center", va="center", fontsize=7.5, weight="bold", color="#7A4A00",
            bbox=dict(boxstyle="round,pad=0.35", fc="#FFF3D6", ec=AMBER, lw=1.1))

    fig.tight_layout()
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Generate EvidenceGuard-SOC figures")
    ap.add_argument("--outdir", default="evidenceguard/figures",
                    help="Output directory for PNG/PDF figures")
    ap.add_argument("--dpi", type=int, default=300, help="PNG resolution")
    ap.add_argument("--calibration", default="evidenceguard/ccva_calibration_template.csv",
                    help="CSV with CCVA bins (predicted_confidence, observed_accuracy, count)")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cal = Path(args.calibration) if args.calibration else None
    if cal is not None and not cal.exists():
        print(f"WARNING: calibration CSV not found: {cal} — using built-in placeholder")
        cal = None

    fig4_2_preservation(outdir / "fig4_2_digital_evidence_preservation_workflow.png",
                        outdir / "fig4_2_digital_evidence_preservation_workflow.pdf", args.dpi)
    print("wrote fig4_2_digital_evidence_preservation_workflow.{png,pdf}")

    ece, mce, total, synthetic = fig4_4_reliability(
        outdir / "fig4_4_reliability_diagram_ccva.png",
        outdir / "fig4_4_reliability_diagram_ccva.pdf", args.dpi, cal)
    print(f"wrote fig4_4_reliability_diagram_ccva.{{png,pdf}}  "
          f"ECE={ece:.4f} MCE={mce:.4f} N={total} synthetic={synthetic}")

    fig4_5_authorization(outdir / "fig4_5_response_authorization_rcra.png",
                         outdir / "fig4_5_response_authorization_rcra.pdf", args.dpi)
    print("wrote fig4_5_response_authorization_rcra.{png,pdf}")

    fig5_2_graph(outdir / "fig5_2_endpoint_process_graph.png",
                 outdir / "fig5_2_endpoint_process_graph.pdf", args.dpi)
    print("wrote fig5_2_endpoint_process_graph.{png,pdf}")


if __name__ == "__main__":
    main()
