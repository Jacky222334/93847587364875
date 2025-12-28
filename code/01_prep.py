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
        "ecr_anxiety_mean_0_4",
        "ecr_avoidance_mean_0_4",
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
    if "ecr_anxiety_mean_0_4" in df.columns:
        df["anx_z"] = zscore(df["ecr_anxiety_mean_0_4"])
    if "ecr_avoidance_mean_0_4" in df.columns:
        df["avoid_z"] = zscore(df["ecr_avoidance_mean_0_4"])

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
    out_csv = os.path.join(OUT_DIR, "prepared_exotic_dataset.csv")
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


