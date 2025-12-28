import os
import json
import numpy as np
import pandas as pd

from utils import OUT_DIR, ensure_dirs, write_json, write_md, now_iso


SEED = 1337
np.random.seed(SEED)


def _ols_fit(X: np.ndarray, y: np.ndarray):
    # add intercept
    X_ = np.column_stack([np.ones(X.shape[0]), X])
    beta = np.linalg.lstsq(X_, y, rcond=None)[0]
    yhat = X_ @ beta
    resid = y - yhat
    n, k = X_.shape
    # HC3 robust SE
    XtX_inv = np.linalg.inv(X_.T @ X_)
    h = np.sum(X_ * (X_ @ XtX_inv), axis=1)
    denom = (1 - h) ** 2
    denom[denom == 0] = np.nan
    omega = (resid ** 2) / denom
    meat = (X_.T * omega) @ X_
    vcov_hc3 = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.diag(vcov_hc3))
    return beta, se, yhat, resid


def _design(df: pd.DataFrame, cols):
    X = df[cols].astype(float).to_numpy()
    return X


def main():
    ensure_dirs()
    in_csv = os.path.join(OUT_DIR, "prepared_pua_dataset.csv")
    df = pd.read_csv(in_csv)

    # core covariates (use what's available)
    covars = ["cci_z", "opsev_z", "onco_z"]
    if "age_z" in df.columns:
        covars.append("age_z")
    if "sex_bin" in df.columns:
        covars.append("sex_bin")

    # baseline model: PCI³ ~ objective burden (+ optional demographics)
    outcome = "periop_intensity_index_z"
    needed = [outcome] + covars
    df_b = df.dropna(subset=needed).copy()
    Xb = _design(df_b, covars)
    yb = df_b[outcome].astype(float).to_numpy()

    beta_b, se_b, yhat_b, resid_b = _ols_fit(Xb, yb)
    df_b["pci3_pred_baseline"] = yhat_b
    df_b["PUA_residual"] = resid_b

    # attachment response surface model
    # anx_z + avoid_z + anx^2 + anx:avoid + avoid^2 + covars
    df_m = df_b.dropna(subset=["anx_z", "avoid_z"]).copy()
    df_m["anx2"] = df_m["anx_z"] ** 2
    df_m["avoid2"] = df_m["avoid_z"] ** 2
    df_m["anx_x_avoid"] = df_m["anx_z"] * df_m["avoid_z"]

    predictors = ["anx_z", "avoid_z", "anx2", "anx_x_avoid", "avoid2"] + covars
    Xm = _design(df_m, predictors)
    ym = df_m[outcome].astype(float).to_numpy()

    beta_m, se_m, yhat_m, resid_m = _ols_fit(Xm, ym)
    df_m["pci3_pred_full"] = yhat_m

    # surface parameters (using coefficients without intercept)
    # beta vector includes intercept at [0]
    # mapping:
    # b1=anx_z, b2=avoid_z, b3=anx2, b4=anx_x_avoid, b5=avoid2
    b1, b2, b3, b4, b5 = beta_m[1:6]
    a1 = b1 + b2
    a2 = b3 + b4 + b5
    a3 = b1 - b2
    a4 = b3 - b4 + b5

    # Model fit summaries
    def r2(y, yhat):
        ssr = np.sum((y - yhat) ** 2)
        sst = np.sum((y - np.mean(y)) ** 2)
        return 1 - ssr / sst if sst > 0 else np.nan

    r2_baseline = r2(yb, yhat_b)
    r2_full = r2(ym, yhat_m)
    delta_r2 = r2_full - r2_baseline

    out = {
        "timestamp": now_iso(),
        "seed": SEED,
        "n_baseline": int(df_b.shape[0]),
        "n_full": int(df_m.shape[0]),
        "covariates_used": covars,
        "baseline": {
            "predictors": covars,
            "r2": float(r2_baseline),
            "beta": beta_b.tolist(),
            "se_hc3": se_b.tolist(),
        },
        "full_response_surface": {
            "predictors": predictors,
            "r2": float(r2_full),
            "delta_r2_vs_baseline": float(delta_r2),
            "beta": beta_m.tolist(),
            "se_hc3": se_m.tolist(),
            "surface_params": {"a1": float(a1), "a2": float(a2), "a3": float(a3), "a4": float(a4)},
        },
    }

    write_json(os.path.join(OUT_DIR, "model_results.json"), out)

    # Save modeling dataset with predictions/residuals
    df_m.to_csv(os.path.join(OUT_DIR, "modeling_dataset_with_predictions.csv"), index=False)

    # Compact tables (CSV)
    # Table 2: main model coefficients (unstandardized B on z-scaled outcome)
    rows = []
    names = ["Intercept"] + predictors
    for name, b, se in zip(names, beta_m, se_m):
        rows.append({"term": name, "B": b, "SE_HC3": se})
    pd.DataFrame(rows).to_csv(os.path.join(OUT_DIR, "tables", "table2_main_model_coeffs.csv"), index=False)

    pd.DataFrame(
        [
            {"param": "a1 (slope congruence)", "value": a1},
            {"param": "a2 (curvature congruence)", "value": a2},
            {"param": "a3 (slope incongruence)", "value": a3},
            {"param": "a4 (curvature incongruence)", "value": a4},
        ]
    ).to_csv(os.path.join(OUT_DIR, "tables", "table2_surface_params.csv"), index=False)

    pd.DataFrame(
        [
            {"model": "baseline", "r2": r2_baseline},
            {"model": "full_response_surface", "r2": r2_full},
            {"model": "delta_r2_full_minus_baseline", "r2": delta_r2},
        ]
    ).to_csv(os.path.join(OUT_DIR, "tables", "table3_model_comparison.csv"), index=False)

    write_md(
        os.path.join(OUT_DIR, "results_snippets.md"),
        f"""## Results snippets (auto-generated; update after Bayesian run if desired)

### Primary model (PCI³; response surface; robust OLS HC3 fallback)
In the core model including objective burden covariates ({", ".join(covars)}), the response-surface specification for attachment dimensions (anxiety, avoidance, quadratic terms, and interaction) explained **R² = {r2_full:.3f}** of variance in PCI³. Surface parameters were: **a1={a1:.3f}**, **a2={a2:.3f}**, **a3={a3:.3f}**, **a4={a4:.3f}** (see `table2_surface_params.csv`).

### Incremental value vs objective burden baseline
Compared to the baseline model (objective burden only; R² = {r2_baseline:.3f}), adding the attachment response surface improved model fit by **ΔR² = {delta_r2:.3f}** (frequentist fallback metric; consider LOO/WAIC if Bayesian libraries are enabled).

### Sensitivity / robustness
This scaffold uses heteroskedasticity-robust HC3 standard errors and z-scaled composites. We recommend sensitivity checks using alternative index definitions (leave-one-component-out) and distribution-aware models for raw counts where applicable.

### Clinical interpretation (template)
PUA can be conceptualized as the residual intensity beyond objective burden. Positive PUA indicates greater-than-expected peri-intake care/intervention intensity and may reflect interpersonal regulation patterns (e.g., attachment-related reassurance dynamics) interacting with care pathways.
""",
    )

    print("✓ Models complete. Wrote:", os.path.join(OUT_DIR, "model_results.json"))


if __name__ == "__main__":
    main()


