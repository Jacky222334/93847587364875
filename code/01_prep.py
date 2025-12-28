import os
import pandas as pd

from utils import (
    ROOT, BASE_DIR, OUT_DIR,
    ensure_dirs, zscore, log1p_safe, write_json, write_md, now_iso
)


DATA_XLSX = os.path.join(
    ROOT,
    "MAJOR_T1_NUMERIC_ONLY_SCORES_HADS_FBK_LPFS_ECR_IMPUTED_GENERALKONSENT_J_ONLY.xlsx",
)

def _cronbach_alpha_listwise(df: pd.DataFrame, cols: list[str]) -> tuple[float, int, int]:
    """
    Cronbach's alpha with listwise complete cases.
    Returns (alpha, n_complete, k_items).
    """
    import numpy as np

    if not cols:
        return float("nan"), 0, 0
    x = df[cols].apply(pd.to_numeric, errors="coerce")
    x = x.dropna(axis=0, how="any")
    n = int(x.shape[0])
    k = int(x.shape[1])
    if n == 0 or k < 2:
        return float("nan"), n, k
    arr = x.to_numpy(dtype=float)
    var_items = np.var(arr, axis=0, ddof=1)
    total = arr.sum(axis=1)
    var_total = np.var(total, ddof=1)
    if var_total == 0 or np.isnan(var_total):
        return float("nan"), n, k
    alpha = (k / (k - 1)) * (1 - (var_items.sum() / var_total))
    return float(alpha), n, k


def _compute_ecr_rescored_0_4(df: pd.DataFrame) -> tuple[pd.Series | None, pd.Series | None, dict]:
    """
    Compute ECR-RD12 anxiety/avoidance subscales (0–4) from item columns.

    Keying used here matches the project's validation file (Validat.md) and yields
    acceptable internal consistency in this dataset:
      - anxiety: items 1, 2, 5, 8, 10, 11
      - avoidance: items 3, 4, 6, 7, 9, 12
      - reverse-coded items: 3, 4, 9, 12 via (4 - x)
    """
    item_cols = {i: f"ECR_RD12_{i}_num_0_4" for i in range(1, 13)}
    missing = [c for c in item_cols.values() if c not in df.columns]
    meta: dict = {
        "ecr_rescore_attempted": True,
        "ecr_item_cols_missing": missing,
        "ecr_keying": {
            "anxiety_items": [1, 2, 5, 8, 10, 11],
            "avoidance_items": [3, 4, 6, 7, 9, 12],
            "reverse_items": [3, 4, 9, 12],
            "reverse_rule": "x_rev = 4 - x",
            "scale": "0-4",
        },
    }
    if missing:
        meta["ecr_rescore_used"] = False
        return None, None, meta

    # Numeric coercion
    items = {i: pd.to_numeric(df[item_cols[i]], errors="coerce") for i in range(1, 13)}
    # Reverse-coded items
    for i in [3, 4, 9, 12]:
        items[i] = 4 - items[i]

    anx_items = [1, 2, 5, 8, 10, 11]
    avoid_items = [3, 4, 6, 7, 9, 12]
    anx = pd.concat([items[i] for i in anx_items], axis=1).mean(axis=1)
    avoid = pd.concat([items[i] for i in avoid_items], axis=1).mean(axis=1)

    # Reliability (listwise complete on the used item keys)
    anx_alpha, anx_n, anx_k = _cronbach_alpha_listwise(df.assign(**{f"__ecr_{i}": items[i] for i in anx_items}),
                                                       [f"__ecr_{i}" for i in anx_items])
    avoid_alpha, avoid_n, avoid_k = _cronbach_alpha_listwise(df.assign(**{f"__ecr_{i}": items[i] for i in avoid_items}),
                                                             [f"__ecr_{i}" for i in avoid_items])
    meta.update({
        "ecr_rescore_used": True,
        "ecr_alpha": {
            "anxiety_alpha": anx_alpha,
            "anxiety_n_listwise": anx_n,
            "anxiety_k": anx_k,
            "avoidance_alpha": avoid_alpha,
            "avoidance_n_listwise": avoid_n,
            "avoidance_k": avoid_k,
        },
    })
    return anx, avoid, meta


def main():
    ensure_dirs()

    df = pd.read_excel(DATA_XLSX)
    audit = {
        "timestamp": now_iso(),
        "input_file": DATA_XLSX,
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "columns": list(df.columns),
    }

    # Required columns (minimum)
    required = [
        "PID",
        "CCI_altersadjustiert",
        "OP_Schweregrad_plus30_Hoechster",
        "oncology_activity_z",
        "utilization_shortterm_z",
        "pharmaburden_z",
        "pain_burden_z",
        "sedation_risk_z",
    ]
    missing_req = [c for c in required if c not in df.columns]
    audit["missing_required_columns"] = missing_req

    # Optional covariates
    if "age" not in df.columns:
        # If no age column exists, we keep it missing and proceed with a reduced covariate set.
        audit["age_note"] = "Column 'age' not found; models will omit age unless user adds it."
    if "sex_bin" not in df.columns:
        audit["sex_note"] = "Column 'sex_bin' not found; models will omit sex unless user adds it."

    # Standardized predictors/covariates
    # Attachment (ECR-RD12): prefer deterministic re-scoring from item columns if available.
    anx_resc, avoid_resc, ecr_meta = _compute_ecr_rescored_0_4(df)
    audit.update(ecr_meta)
    if anx_resc is not None and avoid_resc is not None:
        df["ecr_anxiety_mean_0_4_rescored"] = anx_resc
        df["ecr_avoidance_mean_0_4_rescored"] = avoid_resc
        df["anx_z"] = zscore(df["ecr_anxiety_mean_0_4_rescored"])
        df["avoid_z"] = zscore(df["ecr_avoidance_mean_0_4_rescored"])
        audit["ecr_scoring_source"] = "rescored_from_items"
    else:
        # Fallback: use precomputed score columns
        if "ecr_anxiety_mean_0_4" in df.columns:
            df["anx_z"] = zscore(df["ecr_anxiety_mean_0_4"])
        if "ecr_avoidance_mean_0_4" in df.columns:
            df["avoid_z"] = zscore(df["ecr_avoidance_mean_0_4"])
        audit["ecr_scoring_source"] = "existing_score_columns_fallback"

    if "CCI_altersadjustiert" in df.columns:
        df["cci_z"] = zscore(df["CCI_altersadjustiert"])
    if "OP_Schweregrad_plus30_Hoechster" in df.columns:
        df["opsev_z"] = zscore(df["OP_Schweregrad_plus30_Hoechster"])
    if "oncology_activity_z" in df.columns:
        df["onco_z"] = zscore(df["oncology_activity_z"])
    if "age" in df.columns:
        df["age_z"] = zscore(df["age"])

    # Primary index PCI³
    components = [
        "utilization_shortterm_z",
        "pharmaburden_z",
        "pain_burden_z",
        "sedation_risk_z",
    ]

    if "lab_postop_Anzahl" in df.columns:
        df["lab_postop_z"] = zscore(log1p_safe(df["lab_postop_Anzahl"]))
        components.append("lab_postop_z")

    audit["pci3_components"] = components

    df["periop_intensity_index_z"] = df[components].mean(axis=1, skipna=False)

    # Save prepared dataset
    out_csv = os.path.join(OUT_DIR, "prepared_pua_dataset.csv")
    df.to_csv(out_csv, index=False)
    audit["output_csv"] = out_csv

    # Missingness summary
    miss = df[components + ["anx_z", "avoid_z", "cci_z", "opsev_z", "onco_z"]].isna().mean().sort_values(ascending=False)
    miss_path = os.path.join(OUT_DIR, "tables", "missingness_core.csv")
    miss.to_csv(miss_path, header=["missing_fraction"])

    # Write logs
    write_json(os.path.join(OUT_DIR, "audit.json"), audit)
    write_md(
        os.path.join(OUT_DIR, "analysis_log.md"),
        f"""## Exotic manuscript pipeline — analysis log

- **timestamp**: {audit['timestamp']}
- **input**: `{DATA_XLSX}`
- **rows/cols**: {audit['n_rows']} / {audit['n_cols']}
- **missing required columns**: {missing_req if missing_req else "none"}
- **PCI³ components**: {", ".join(components)}
- **prepared dataset**: `{out_csv}`
""",
    )

    print("✓ Prepared dataset written:", out_csv)
    print("✓ Audit written:", os.path.join(OUT_DIR, "audit.json"))


if __name__ == "__main__":
    main()


