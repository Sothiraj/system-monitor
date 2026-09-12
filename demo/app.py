"""
CBAN — Class-Balanced Attention Network for Network Intrusion Detection.
Streamlit demo dashboard.

Shows:
  * live inference on any NSL-KDD connection record (pick a real test sample,
    upload a CSV, or type raw feature values)
  * per-prediction explanation (learned feature-attention + top contributing
    features)
  * comparison of CBAN against baselines (accuracy / F1 / false-alarm rate)
  * confusion matrices, per-class F1, attention ranking, architecture diagram

Run:  streamlit run demo/app.py --server.address 0.0.0.0 --server.port 8501 \
        --server.headless true --server.enableCORS false \
        --server.enableXsrfProtection false
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st
import tensorflow as tf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
from models import FeatureAttention  # noqa: E402  (register custom Keras layer)

MODEL_DIR = ROOT / "results" / "models"
FIG_DIR = ROOT / "results" / "figures"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

CUSTOM_OBJECTS = {"FeatureAttention": FeatureAttention}

tf.get_logger().setLevel("ERROR")

st.set_page_config(page_title="CBAN Intrusion Detection", page_icon="🛡️", layout="wide")


# --------------------------------------------------------------------------
# Loading helpers
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_artifacts():
    meta = json.load(open(MODEL_DIR / "meta.json"))
    proc = joblib.load(MODEL_DIR / "processor.joblib")
    full = tf.keras.models.load_model(MODEL_DIR / "cban_full.h5", compile=False,
                                      custom_objects=CUSTOM_OBJECTS)
    attn = np.load(MODEL_DIR / "attn_weights.npy")
    return meta, proc, full, attn


@st.cache_data(show_spinner=False)
def load_metrics():
    m5 = json.load(open(RESULTS_DIR / "metrics_5class.json"))
    m13 = json.load(open(RESULTS_DIR / "metrics_13class.json"))
    return m5, m13


@st.cache_data(show_spinner=False)
def load_test_records():
    from preprocess import FEATURE_NAMES, load_raw

    return load_raw(DATA_DIR / "KDDTest+.txt"), FEATURE_NAMES


def predict_row(proc, full, meta, raw_series: pd.Series) -> tuple[str, np.ndarray]:
    row = pd.DataFrame([raw_series])
    x = proc.transform(row).astype(np.float32)
    proba = full.predict(x, verbose=0)[0]
    pred = int(np.argmax(proba))
    return meta["class_names"][pred], proba


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
st.sidebar.title("🛡️ CBAN — NIDS Demo")
st.sidebar.markdown(
    "**Class-Balanced Attention Network** for network intrusion detection.\n\n"
    "Feature-attention encoder trained with focal loss + class weights, "
    "followed by a softmax head. Built on Shone et al., IEEE TETCI 2018."
)

mode = st.sidebar.radio(
    "Input mode",
    ["🔍 Pick a real test sample", "📄 Upload raw NSL-KDD CSV", "⌨️ Enter feature values"],
)

# --------------------------------------------------------------------------
# Load data / artifacts (with graceful degradation)
# --------------------------------------------------------------------------
artifacts_ready = (MODEL_DIR / "cban_full.h5").exists()

if not artifacts_ready:
    st.warning("⚠️ Trained models not found. Run `python code/train_all.py` first.")
    st.stop()

meta, proc, full, attn = load_artifacts()
m5, m13 = load_metrics()
class_names = meta["class_names"]
feature_names = meta["feature_names"]

st.title("🛡️ Class-Balanced Attention Network for Network Intrusion Detection")
st.caption(
    "Enhanced deep-learning NIDS based on Shone et al., *A Deep Learning Approach to Network "
    "Intrusion Detection*, IEEE TETCI 2(1):41–50, 2018 — with a learned feature-attention gate, "
    "focal loss, and class weights to fix the rare-class (R2L/U2R) detection gap."
)

# --------------------------------------------------------------------------
# Inference panel
# --------------------------------------------------------------------------
st.header("1 · Live inference")
col_input, col_pred = st.columns([1.2, 1])
raw = None

with col_input:
    if mode == "🔍 Pick a real test sample":
        df_test, _ = load_test_records()
        interesting = ["normal", "neptune", "satan", "guess_passwd", "buffer_overflow",
                       "portsweep", "ipsweep", "smurf", "back", "warezmaster"]
        options = []
        for lab in interesting:
            sub = df_test[df_test["label"] == lab]
            if len(sub):
                options.append((lab, sub.index[0]))
        if options:
            sel_lab = st.selectbox("Attack family", [o[0] for o in options])
            idx = [o[1] for o in options if o[0] == sel_lab][0]
        else:
            idx = 0
        if st.button("🎲 Random test sample", width="stretch"):
            idx = int(np.random.choice(df_test.index))
        raw = df_test.loc[idx]
        st.markdown(f"**True label:** `{raw['label']}` (sample #{idx})")

    elif mode == "📄 Upload raw NSL-KDD CSV":
        st.markdown("Upload rows with the 41 NSL-KDD columns (`duration,…,dst_host_srv_rerror_rate[,label]`).")
        up = st.file_uploader("CSV file", type=["csv"])
        if up is not None:
            df_up = pd.read_csv(up, header=None)
            raw = df_up.iloc[0]
            st.markdown(f"**Row 0 of {len(df_up)}**")
        else:
            st.info("Awaiting upload…")

    else:  # manual entry
        st.markdown("Enter the 41 connection features (protocol_type, service, flag are symbolic).")
        from preprocess import CATEGORICAL, NUMERIC

        raw_dict = {}
        for c in CATEGORICAL:
            raw_dict[c] = st.selectbox(
                c, ["tcp", "udp", "icmp"] if c == "protocol_type" else
                (["http", "ftp_data", "smtp", "private", "other", "domain_u"] if c == "service" else
                 ["SF", "S0", "REJ", "RSTO", "RSTR", "SH", "S1", "S2", "S3", "OTH"]))
        for n in NUMERIC:
            raw_dict[n] = st.number_input(n, value=0.0, step=1.0, format="%.4f")
        raw = pd.Series(raw_dict)

with col_pred:
    if raw is not None:
        try:
            pred_label, proba = predict_row(proc, full, meta, raw)
            order = np.argsort(proba)[::-1]
            st.markdown("#### Prediction")
            color = "red" if pred_label != "normal" else "green"
            st.markdown(f"### :{color}[{pred_label.upper()}]")
            conf = float(proba.max()) * 100
            st.progress(int(conf), text=f"confidence {conf:.1f}%")
            for i in order:
                st.write(f"- {class_names[i].upper():<8} {proba[i]*100:5.1f}%")
        except Exception as e:  # noqa: BLE001
            st.error(f"Inference error: {e}")

# --------------------------------------------------------------------------
# Explanation
# --------------------------------------------------------------------------
st.header("2 · Why this prediction? (built-in explanation)")
colA, colB = st.columns([1, 1])
with colA:
    top = np.argsort(attn)[::-1][:15]
    names = [feature_names[i] for i in top][::-1]
    vals = (attn[top] * 100)[::-1]
    st.bar_chart(pd.DataFrame({"feature": names, "attention %": vals}).set_index("feature"), height=360)
    st.caption("Learned feature-attention weights (softmax over the 122 input features).")
with colB:
    if raw is not None:
        try:
            xflat = proc.transform(pd.DataFrame([raw])).flatten()
            contrib = attn * xflat
            idxs = np.argsort(np.abs(contrib))[::-1][:15]
            dfc = pd.DataFrame({
                "feature": [feature_names[i] for i in idxs],
                "value": [float(xflat[i]) for i in idxs],
                "attention-weighted": [float(contrib[i]) for i in idxs],
            })
            st.dataframe(dfc, width="stretch", height=360)
        except Exception as e:  # noqa: BLE001
            st.info("Enter or pick a sample to see per-feature contribution.")

# --------------------------------------------------------------------------
# Results comparison
# --------------------------------------------------------------------------
st.header("3 · Results vs. baselines (NSL-KDD, 5-class)")
st.markdown(
    "Shone et al. reported **85.42 %** accuracy (S-NDAE+RF) and **80.58 %** (DBN) on 5-class NSL-KDD, "
    "with **0 % R2L / U2R recall**. Below: our re-implementation and the proposed CBAN on the "
    "**filtered** test protocol (18,794 records, the paper's setting) and the **full** KDDTest+ (22,544 records)."
)

rows = []
for m in ["RF (raw features)", "MLP (deep baseline)", "NDAE + RF (Shone re-impl.)",
          "CBAN w/o focal", "CBAN w/o attention", "CBAN (proposed)"]:
    r_f = m5.get(f"filtered::{m}")
    if r_f is None:
        continue
    rows.append({
        "model": m,
        "acc (filtered)": r_f["accuracy"],
        "F1 macro (filtered)": r_f["f1_macro"],
        "R2L recall": r_f["per_class"]["r2l"]["recall"],
        "U2R recall": r_f["per_class"]["u2r"]["recall"],
        "false alarm": r_f["false_alarm_rate"],
        "acc (full)": m5.get(f"full::{m}", {}).get("accuracy", float("nan")),
    })
df_acc = pd.DataFrame(rows).set_index("model")
st.dataframe((df_acc * 100).round(2).rename(columns=lambda c: c + " %"), width="stretch")

tabs = st.tabs(["Confusion matrices", "Per-class F1", "Attention ranking", "Architecture", "13-class"])
with tabs[0]:
    if (FIG_DIR / "fig2_confusion.png").exists():
        st.image(str(FIG_DIR / "fig2_confusion.png"), width="stretch")
with tabs[1]:
    if (FIG_DIR / "fig3_per_class_f1.png").exists():
        st.image(str(FIG_DIR / "fig3_per_class_f1.png"), width="stretch")
with tabs[2]:
    if (FIG_DIR / "fig4_attention.png").exists():
        st.image(str(FIG_DIR / "fig4_attention.png"), width="stretch")
with tabs[3]:
    if (FIG_DIR / "fig1_architecture.png").exists():
        st.image(str(FIG_DIR / "fig1_architecture.png"), width="stretch")
with tabs[4]:
    if (FIG_DIR / "fig7_13class_f1.png").exists():
        st.image(str(FIG_DIR / "fig7_13class_f1.png"), width="stretch")
    for m in ("RF (raw features)", "NDAE + RF (Shone re-impl.)", "CBAN (proposed)"):
        r = m13.get(f"filtered::{m}")
        if r:
            st.markdown(f"**{m}** — filtered accuracy {r['accuracy']*100:.2f}%, F1(macro) {r['f1_macro']*100:.2f}%")

st.sidebar.divider()
st.sidebar.caption(
    "NSL-KDD benchmark · paper: docs/paper/CBAN_IEEE_Paper.pdf\n"
    "Reproduce: `python code/train_all.py`"
)
