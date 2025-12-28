import os
import json
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = "/home/jbs123/Dokumente/intake"
BASE_DIR = os.path.join(ROOT, "04_exotic_manis")
OUT_DIR = os.path.join(BASE_DIR, "outputs_pua")


def ensure_dirs():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "tables"), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "figures"), exist_ok=True)


def zscore(series: pd.Series) -> pd.Series:
    s = series.astype(float)
    mu = s.mean(skipna=True)
    sd = s.std(skipna=True, ddof=0)
    if sd == 0 or np.isnan(sd):
        return (s - mu) * 0.0
    return (s - mu) / sd


def log1p_safe(series: pd.Series) -> pd.Series:
    s = series.astype(float).copy()
    # ensure non-negative for count-like data
    s[s < 0] = np.nan
    return np.log1p(s)


def write_json(path: str, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def write_md(path: str, text: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


