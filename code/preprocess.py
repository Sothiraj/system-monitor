"""
NSL-KDD preprocessing.

Converts the raw KDDTrain+.txt / KDDTest+.txt files (41 features) into a
numeric, normalized feature matrix via:
  * one-hot encoding of the 3 symbolic features (protocol_type, service, flag)
  * min-max scaling of the 38 numeric features
  * label mapping to the 5 attack categories (or the 13-class granular split)

The processor object (NSLKDDProcessor) is picklable so the same fitted
encoders/scalers can be reused by the live demo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

# --------------------------------------------------------------------------
# Feature schema (KDD Cup '99 / NSL-KDD)
# --------------------------------------------------------------------------
FEATURE_NAMES = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in",
    "num_compromised", "root_shell", "su_attempted", "num_root",
    "num_file_creations", "num_shells", "num_access_files", "num_outbound_cmds",
    "is_host_login", "is_guest_login", "count", "srv_count", "serror_rate",
    "srv_serror_rate", "rerror_rate", "srv_rerror_rate", "same_srv_rate",
    "diff_srv_rate", "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate", "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate",
]

CATEGORICAL = ["protocol_type", "service", "flag"]
NUMERIC = [f for f in FEATURE_NAMES if f not in CATEGORICAL]

# Official NSL-KDD attack -> category mapping (from Attack Types.csv).
ATTACK_TO_CLASS = {
    "back": "dos", "land": "dos", "neptune": "dos", "pod": "dos",
    "smurf": "dos", "teardrop": "dos", "apache2": "dos", "mailbomb": "dos",
    "processtable": "dos", "udpstorm": "dos",
    "ipsweep": "probe", "nmap": "probe", "portsweep": "probe",
    "satan": "probe", "mscan": "probe", "saint": "probe",
    "ftp_write": "r2l", "guess_passwd": "r2l", "imap": "r2l",
    "multihop": "r2l", "phf": "r2l", "spy": "r2l", "warezclient": "r2l",
    "warezmaster": "r2l", "named": "r2l", "sendmail": "r2l",
    "snmpgetattack": "r2l", "snmpguess": "r2l", "xlock": "r2l",
    "xsnoop": "r2l", "httptunnel": "r2l", "worm": "r2l",
    "buffer_overflow": "u2r", "loadmodule": "u2r", "perl": "u2r",
    "rootkit": "u2r", "ps": "u2r", "sqlattack": "u2r", "xterm": "u2r",
    "normal": "normal",
}

CLASS_NAMES_5 = ["normal", "dos", "probe", "r2l", "u2r"]

# The 13 labels (normal + 12 attack families) used in Shone et al. Table 5.
CLASS_NAMES_13 = [
    "normal", "back", "buffer_overflow", "guess_passwd", "ipsweep", "neptune",
    "nmap", "pod", "portsweep", "satan", "smurf", "teardrop", "warezclient",
]


def load_raw(path: str) -> pd.DataFrame:
    """Load a raw NSL-KDD txt file into a DataFrame."""
    cols = FEATURE_NAMES + ["label", "difficulty"]
    df = pd.read_csv(path, header=None, names=cols)
    return df


@dataclass
class ProcessedData:
    X_train: np.ndarray
    y_train: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    feature_names: list = field(default_factory=list)
    class_names: list = field(default_factory=list)
    y_train_raw: np.ndarray = None
    y_test_raw: np.ndarray = None


class NSLKDDProcessor:
    """Fits one-hot encoders + min-max scaler; transforms raw DataFrames."""

    def __init__(self):
        self.cat_vocab: dict[str, list] = {}
        self.scaler = MinMaxScaler(clip=False)
        self.feature_names: list[str] = []
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> "NSLKDDProcessor":
        for c in CATEGORICAL:
            self.cat_vocab[c] = sorted(df[c].astype(str).unique())
        self.scaler.fit(df[NUMERIC].values.astype(np.float64))
        self.feature_names = self._make_feature_names()
        self._fitted = True
        return self

    def _make_feature_names(self) -> list[str]:
        names = []
        for c in CATEGORICAL:
            names += [f"{c}={v}" for v in self.cat_vocab[c]]
        names += NUMERIC
        return names

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Processor must be fit before transform.")
        parts = []
        for c in CATEGORICAL:
            vals = df[c].astype(str).values
            onehot = np.zeros((len(vals), len(self.cat_vocab[c])), dtype=np.float32)
            for i, v in enumerate(self.cat_vocab[c]):
                onehot[:, i] = (vals == v)
            parts.append(onehot)
        numeric = self.scaler.transform(df[NUMERIC].values.astype(np.float64))
        parts.append(numeric.astype(np.float32))
        return np.hstack(parts).astype(np.float32)

    # -- persistence -------------------------------------------------------
    def save(self, path: str) -> None:
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "NSLKDDProcessor":
        return joblib.load(path)


def map_labels(df: pd.DataFrame, n_class: int) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return (y_encoded, y_raw_attack_names, class_names)."""
    attack = df["label"].str.strip().str.lower().str.replace(r"\.$", "", regex=True)
    if n_class == 5:
        class_names = CLASS_NAMES_5
        cat = attack.map(lambda a: ATTACK_TO_CLASS.get(a, "normal"))
        idx = {c: i for i, c in enumerate(class_names)}
        y = np.array([idx.get(c, 0) for c in cat], dtype=np.int64)
    elif n_class == 13:
        class_names = CLASS_NAMES_13
        idx = {c: i for i, c in enumerate(class_names)}
        y = np.array([idx.get(a, 0) for a in attack], dtype=np.int64)
    else:
        raise ValueError("n_class must be 5 or 13")
    return y, attack.values, class_names


def load_preprocessed(
    train_path: str, test_path: str, n_class: int = 5
) -> tuple[ProcessedData, NSLKDDProcessor]:
    """Load, fit and transform the train/test split into numeric arrays."""
    df_train = load_raw(train_path)
    df_test = load_raw(test_path)

    # Vocabulary is built over the union of train + test so that test-only
    # attack families (e.g. 'saint', 'xterm') still receive a valid encoding.
    proc = NSLKDDProcessor()
    proc.fit(pd.concat([df_train, df_test], ignore_index=True))

    X_train = proc.transform(df_train)
    X_test = proc.transform(df_test)

    y_train, y_train_raw, class_names = map_labels(df_train, n_class)
    y_test, y_test_raw, _ = map_labels(df_test, n_class)

    return (
        ProcessedData(
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            feature_names=proc.feature_names,
            class_names=class_names,
            y_train_raw=y_train_raw,
            y_test_raw=y_test_raw,
        ),
        proc,
    )


def known_attack_mask(train_path: str, test_path: str) -> np.ndarray:
    """Boolean mask of test records whose attack family appears in the training set.

    The base paper evaluated on a filtered test subset (18,794 records) that
    excludes novel attack families absent from the training data; this helper
    reproduces that protocol for a fair head-to-head comparison.
    """
    tr_raw = (
        load_raw(train_path)["label"]
        .str.strip().str.lower().str.replace(r"\.$", "", regex=True)
    )
    te_raw = (
        load_raw(test_path)["label"]
        .str.strip().str.lower().str.replace(r"\.$", "", regex=True)
    )
    known = set(tr_raw.unique())
    return te_raw.isin(known).values


def download_data(data_dir: str = "data") -> None:
    """Best-effort helper to fetch the NSL-KDD txt files from GitHub."""
    import subprocess
    import shutil
    import tempfile

    os.makedirs(data_dir, exist_ok=True)
    if os.path.exists(os.path.join(data_dir, "KDDTrain+.txt")) and os.path.exists(
        os.path.join(data_dir, "KDDTest+.txt")
    ):
        print("[preprocess] data already present, skipping download.")
        return
    with tempfile.TemporaryDirectory() as tmp:
        print("[preprocess] cloning NSL_KDD mirror ...")
        subprocess.run(
            ["git", "clone", "--depth", "1",
             "https://github.com/defcom17/NSL_KDD.git", tmp],
            check=True,
        )
        for f in ("KDDTrain+.txt", "KDDTest+.txt"):
            shutil.copy(os.path.join(tmp, f), os.path.join(data_dir, f))
    print("[preprocess] data ready in", data_dir)
