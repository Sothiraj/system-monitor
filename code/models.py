"""
Model zoo for the NIDS experiments.

Baselines:
  * RF-raw      : Random Forest on raw one-hot/scaled features (shallow head)
  * MLP         : plain deep feed-forward network (deep baseline)
  * NDAE+RF     : stacked autoencoder + Random Forest (re-implementation of
                  Shone et al., IEEE TETCI 2018 -- the base paper)

Proposed (CBAN):
  * CBAN-D      : Class-Balanced Attention Network, deep head only
                  (feature-attention gate + focal loss + class weights)
  * CBAN (full) : CBAN encoder -> targeted SMOTE on embeddings -> Random Forest

Everything is seeded for reproducibility and runs on CPU.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

import numpy as np
import tensorflow as tf
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from tensorflow.keras import Model, Input, layers
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.optimizers import Adam

SEED = 42
tf.random.set_seed(SEED)
np.random.seed(SEED)

# --------------------------------------------------------------------------
# Layers
# --------------------------------------------------------------------------

@tf.keras.utils.register_keras_serializable(package="CBAN")
class FeatureAttention(layers.Layer):
    """Soft feature-attention gate.

    Learns a per-feature importance mask w = softmax(theta) and multiplies
    the input element-wise, so the network can down-weight noisy features and
    up-weight discriminative ones. The mask is directly inspectable, which
    gives the model a built-in explanation for every prediction.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self, input_shape):
        d = int(input_shape[-1])
        self.theta = self.add_weight(
            name="attn_theta", shape=(d,), initializer="glorot_uniform", trainable=True
        )
        super().build(input_shape)

    def call(self, inputs):
        w = tf.nn.softmax(self.theta, axis=-1)
        return inputs * w

    def attention_weights(self) -> np.ndarray:
        return tf.nn.softmax(self.theta, axis=-1).numpy()


# --------------------------------------------------------------------------
# Loss
# --------------------------------------------------------------------------

def focal_loss(gamma: float = 2.0, alpha: Optional[np.ndarray] = None):
    """Categorical focal loss (sparse labels).

    alpha: optional per-class weighting vector; combined with the
    (1 - p)^gamma modulating factor to focus on hard, rare classes.
    """

    def _loss(y_true, y_pred):
        y_true = tf.cast(y_true, tf.int32)
        ce = tf.keras.losses.sparse_categorical_crossentropy(y_true, y_pred, from_logits=False)
        p = tf.reduce_sum(y_pred * tf.one_hot(y_true, tf.shape(y_pred)[-1]), axis=-1)
        w = tf.pow(1.0 - p, gamma)
        if alpha is not None:
            a = tf.gather(tf.constant(alpha, dtype=tf.float32), y_true)
            ce = ce * a
        return w * ce

    return _loss


def class_weights_from(y: np.ndarray) -> dict[int, float]:
    """Inverse-frequency class weights (scikit 'balanced' scheme)."""
    from sklearn.utils.class_weight import compute_class_weight

    w = compute_class_weight("balanced", classes=np.unique(y), y=y)
    return {int(c): float(v) for c, v in zip(np.unique(y), w)}


def alpha_vector(y: np.ndarray, n_classes: int) -> np.ndarray:
    cw = class_weights_from(y)
    return np.array([cw.get(i, 1.0) for i in range(n_classes)], dtype=np.float32)


# --------------------------------------------------------------------------
# Architectures
# --------------------------------------------------------------------------

def build_mlp(input_dim: int, n_classes: int) -> Model:
    inp = Input(shape=(input_dim,), name="x")
    h = layers.Dense(64, activation="relu")(inp)
    h = layers.Dropout(0.3)(h)
    h = layers.Dense(32, activation="relu")(h)
    h = layers.Dropout(0.2)(h)
    out = layers.Dense(n_classes, activation="softmax", name="out")(h)
    return Model(inp, out, name="MLP")


def build_attention_encoder(input_dim: int, n_classes: int, embed_dim: int = 16,
                            use_attention: bool = True) -> tuple[Model, Model]:
    """Feature-attention encoder + softmax classification head.

    Returns (full_model, encoder_model).
    """
    inp = Input(shape=(input_dim,), name="x")
    if use_attention:
        attn_layer = FeatureAttention(name="feature_attention")
        a = attn_layer(inp)
    else:
        a = inp
    h = layers.Dense(64, activation="relu", name="dense1")(a)
    h = layers.Dropout(0.3)(h)
    h = layers.Dense(32, activation="relu", name="dense2")(h)
    h = layers.Dropout(0.2)(h)
    emb = layers.Dense(embed_dim, activation="relu", name="embedding")(h)
    out = layers.Dense(n_classes, activation="softmax", name="out")(emb)

    full = Model(inp, out, name="CBAN")
    encoder = Model(inp, emb, name="CBAN_encoder")
    return full, encoder


def build_ndae(input_dim: int, hidden: tuple[int, ...] = (64, 32, 16)) -> tuple[Model, Model]:
    """Stacked (non-symmetric) autoencoder: encoder + decoder.

    Reproduces the spirit of the base paper's NDAE: a deep encoder whose
    bottleneck representation is fed to Random Forest.
    """
    inp = Input(shape=(input_dim,), name="x")
    h = inp
    for units in hidden:
        h = layers.Dense(units, activation="relu")(h)
    enc_out = h

    h = enc_out
    for units in reversed(hidden[1:]):
        h = layers.Dense(units, activation="relu")(h)
    dec_out = layers.Dense(input_dim, activation="linear")(h)

    auto = Model(inp, dec_out, name="NDAE")
    encoder = Model(inp, enc_out, name="NDAE_encoder")
    return auto, encoder


# --------------------------------------------------------------------------
# Trainers
# --------------------------------------------------------------------------

def _fit_model(
    model: Model,
    X: np.ndarray,
    y: np.ndarray,
    epochs: int = 40,
    batch_size: int = 1024,
    loss=None,
    class_weight: Optional[dict] = None,
    verbose: int = 0,
) -> tuple[Model, float]:
    model.compile(optimizer=Adam(learning_rate=1e-3), loss=loss or "sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    X_tr, X_va, y_tr, y_va = train_test_split(
        X, y, test_size=0.1, random_state=SEED, stratify=y
    )
    es = EarlyStopping(monitor="val_loss", patience=6, restore_best_weights=True, verbose=0)
    t0 = time.time()
    model.fit(
        X_tr, y_tr,
        validation_data=(X_va, y_va),
        epochs=epochs, batch_size=batch_size,
        class_weight=class_weight, callbacks=[es], verbose=verbose,
    )
    return model, time.time() - t0


def train_mlp(X: np.ndarray, y: np.ndarray, n_classes: int) -> tuple[Model, float]:
    model = build_mlp(X.shape[1], n_classes)
    model, t = _fit_model(model, X, y, class_weight=class_weights_from(y))
    return model, t


def train_cban_deep(X: np.ndarray, y: np.ndarray, n_classes: int, gamma: float = 2.0,
                    use_attention: bool = True, use_focal: bool = True,
                    epochs: int = 50) -> tuple[Model, Model, float, np.ndarray]:
    """Train the (attention) encoder end-to-end.

    use_focal=True  -> focal loss (gamma) with inverse-frequency alpha
    use_focal=False -> class-weighted categorical cross-entropy (ablation)
    """
    full, encoder = build_attention_encoder(X.shape[1], n_classes, use_attention=use_attention)
    alpha = alpha_vector(y, n_classes)
    if use_focal:
        loss = focal_loss(gamma=gamma, alpha=alpha)
        cw = None
    else:
        loss = "sparse_categorical_crossentropy"
        cw = class_weights_from(y)
    full, t = _fit_model(full, X, y, epochs=epochs, loss=loss, class_weight=cw)
    attn = None
    if use_attention:
        attn = full.get_layer("feature_attention").attention_weights()
    else:
        attn = np.zeros(X.shape[1], dtype=np.float32)
    return full, encoder, t, attn


def train_ndae(X: np.ndarray, hidden: tuple[int, ...] = (64, 32, 16),
               epochs: int = 40, batch_size: int = 1024) -> tuple[Model, float]:
    auto, encoder = build_ndae(X.shape[1], hidden)
    auto.compile(optimizer=Adam(learning_rate=1e-3), loss="mse")
    es = EarlyStopping(monitor="loss", patience=6, restore_best_weights=True, verbose=0)
    t0 = time.time()
    auto.fit(X, X, epochs=epochs, batch_size=batch_size, callbacks=[es], verbose=0)
    return encoder, time.time() - t0


def train_rf(X: np.ndarray, y: np.ndarray, n_estimators: int = 200) -> tuple[RandomForestClassifier, float]:
    rf = RandomForestClassifier(
        n_estimators=n_estimators, max_features="sqrt", n_jobs=-1,
        random_state=SEED, min_samples_leaf=1, class_weight=None,
    )
    t0 = time.time()
    rf.fit(X, y)
    return rf, time.time() - t0


def targeted_smote(
    X: np.ndarray, y: np.ndarray, target: int = 2000, min_k: int = 1
) -> tuple[np.ndarray, np.ndarray]:
    """Oversample minority classes with fewer than `target` samples up to `target`.

    Only classes with >= 2 samples are resampled (SMOTE needs neighbours);
    k_neighbors is adapted so it never exceeds class size - 1.
    """
    counts = np.bincount(y, minlength=np.max(y) + 1)
    strategy = {}
    for c, n in enumerate(counts):
        if n == 0:
            continue
        if n < target and n >= 2:
            strategy[int(c)] = min(target, max(n, 2))
    if not strategy:
        return X, y
    k = max(min_k, 1)
    # choose a single k for all: 1 is safe for the smallest class
    sm = SMOTE(sampling_strategy=strategy, k_neighbors=1, random_state=SEED)
    Xr, yr = sm.fit_resample(X, y)
    return Xr, yr
