import os
import pandas as pd
import json

from utils import OUT_DIR, ensure_dirs, write_md, now_iso


def _p_from_t_approx(t: float) -> float:
    """
    Two-sided p-value from |t| using a normal approximation.
    We use this because HC3 robust SE are asymptotic; for n~100 the normal approx is standard.
    """
    import math

    z = abs(float(t))
    # Normal CDF via erf
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return float(max(0.0, min(1.0, 2.0 * (1.0 - cdf))))


def _fmt_num(x, nd=3):
    try:
        if pd.isna(x):
            return ""
        return f"{float(x):.{nd}f}"
    except Exception:
        return ""


def _fmt_p(p: float) -> str:
    if pd.isna(p):
        return ""
    p = float(p)
    if p < 0.001:
        return "< .001"
    return f"= {_fmt_num(p, nd=3).lstrip('0')}"


def _write_tex(path: str, text: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def main():
    ensure_dirs()

    df = pd.read_csv(os.path.join(OUT_DIR, "prepared_pua_dataset.csv"))
    # model_results.json is a nested dict; use plain json loader (pandas may error on nested dicts)
    with open(os.path.join(OUT_DIR, "model_results.json"), "r", encoding="utf-8") as f:
        model_res = json.load(f)

    # Table 1: descriptives + missingness (core)
    core_vars = [
        "ecr_anxiety_mean_0_4",
        "ecr_avoidance_mean_0_4",
        "CCI_altersadjustiert",
        "OP_Schweregrad_plus30_Hoechster",
        "oncology_activity_z",
        "utilization_shortterm_z",
        "pharmaburden_z",
        "pain_burden_z",
        "sedation_risk_z",
        "periop_intensity_index_z",
    ]
    core_vars = [c for c in core_vars if c in df.columns]

    desc = []
    for c in core_vars:
        s = pd.to_numeric(df[c], errors="coerce")
        desc.append(
            {
                "variable": c,
                "N": int(s.notna().sum()),
                "missing_n": int(s.isna().sum()),
                "mean": float(s.mean()),
                # Use sample SD (ddof=1) for descriptives.
                "sd": float(s.std(ddof=1)),
                "median": float(s.median()),
                "iqr": float(s.quantile(0.75) - s.quantile(0.25)),
                "min": float(s.min()),
                "max": float(s.max()),
            }
        )
    desc_df = pd.DataFrame(desc)
    desc_df.to_csv(os.path.join(OUT_DIR, "tables", "table1_descriptives.csv"), index=False)

    # --- LaTeX tables for manuscript (reproducible, journal-ready) ---
    labels = {
        "ecr_anxiety_mean_0_4": "Attachment anxiety (0--4)",
        "ecr_avoidance_mean_0_4": "Attachment avoidance (0--4)",
        "CCI_altersadjustiert": "Age-adjusted CCI",
        "OP_Schweregrad_plus30_Hoechster": "Surgical severity (0--5)",
        "oncology_activity_z": "Oncology activity (z)",
        "utilization_shortterm_z": "Utilization intensity (z)",
        "pharmaburden_z": "Pharmacotherapy burden (z)",
        "pain_burden_z": "Pain-related burden (z)",
        "sedation_risk_z": "Sedation risk (z)",
        "periop_intensity_index_z": "PCI$^3$ (z)",
    }

    # Table 1 (tabular only; wrapper/caption live in manuscript .tex)
    t1 = desc_df.copy()
    t1["Variable"] = t1["variable"].map(lambda x: labels.get(x, x))
    t1["Mean"] = t1["mean"].map(lambda x: _fmt_num(x, 3))
    t1["SD"] = t1["sd"].map(lambda x: _fmt_num(x, 3))
    t1["Median"] = t1["median"].map(lambda x: _fmt_num(x, 3))
    t1["Range"] = t1.apply(lambda r: f"{_fmt_num(r['min'], 3)}--{_fmt_num(r['max'], 3)}", axis=1)
    t1["Missing"] = t1.apply(lambda r: f"{int(r['missing_n'])}", axis=1)
    t1 = t1[["Variable", "Mean", "SD", "Median", "Range", "Missing"]]

    t1_tex = t1.to_latex(index=False, escape=False, column_format="lrrrrr", caption=None, label=None)
    # Make it booktabs-friendly (pandas already uses \toprule etc when available).
    _write_tex(os.path.join(OUT_DIR, "tables", "table1_descriptives_tabular.tex"), t1_tex)

    # Table 2 (main model coefficients with t/p/CI) + Surface parameters
    coeffs_csv = os.path.join(OUT_DIR, "tables", "table2_main_model_coeffs.csv")
    surf_csv = os.path.join(OUT_DIR, "tables", "table2_surface_params.csv")
    if os.path.exists(coeffs_csv) and os.path.exists(surf_csv):
        coeffs = pd.read_csv(coeffs_csv)
        surf = pd.read_csv(surf_csv)

        term_labels = {
            "Intercept": "Intercept",
            "anx_z": "Attachment anxiety (z)",
            "avoid_z": "Attachment avoidance (z)",
            "anx2": "Anxiety$^2$",
            "anx_x_avoid": "Anxiety $\\times$ Avoidance",
            "avoid2": "Avoidance$^2$",
            "cci_z": "CCI (z)",
            "opsev_z": "Surgical severity (z)",
            "onco_z": "Oncology activity (z)",
            "age_z": "Age (z)",
            "sex_bin": "Sex (binary)",
        }

        coeffs["Predictor"] = coeffs["term"].map(lambda x: term_labels.get(x, x))
        coeffs["t"] = coeffs["B"] / coeffs["SE_HC3"]
        coeffs["p"] = coeffs["t"].map(_p_from_t_approx)
        coeffs["CI_lo"] = coeffs["B"] - 1.96 * coeffs["SE_HC3"]
        coeffs["CI_hi"] = coeffs["B"] + 1.96 * coeffs["SE_HC3"]

        coeffs_disp = coeffs.copy()
        coeffs_disp["B"] = coeffs_disp["B"].map(lambda x: _fmt_num(x, 3))
        coeffs_disp["SE (HC3)"] = coeffs_disp["SE_HC3"].map(lambda x: _fmt_num(x, 3))
        coeffs_disp["t"] = coeffs_disp["t"].map(lambda x: _fmt_num(x, 2))
        coeffs_disp["p"] = coeffs["p"].map(_fmt_p)
        coeffs_disp["95\\% CI"] = coeffs.apply(
            lambda r: f"[{_fmt_num(r['CI_lo'], 3)}, {_fmt_num(r['CI_hi'], 3)}]", axis=1
        )
        coeffs_disp = coeffs_disp[["Predictor", "B", "SE (HC3)", "t", "p", "95\\% CI"]]

        # Surface parameters (display)
        surf_disp = surf.copy()
        surf_disp["Parameter"] = surf_disp["param"]
        surf_disp["Estimate"] = surf_disp["value"].map(lambda x: _fmt_num(x, 3))
        surf_disp = surf_disp[["Parameter", "Estimate"]]

        # Write a single tabular with two panels (keeps Table 2 self-contained)
        lines = []
        lines.append("\\begin{tabular}{lrrrrr}")
        lines.append("\\toprule")
        lines.append("Predictor & $B$ & SE (HC3) & $t$ & $p$ & 95\\% CI \\\\")
        lines.append("\\midrule")
        lines.append("\\multicolumn{6}{l}{\\textit{Panel A. Regression coefficients}} \\\\")
        for _, r in coeffs_disp.iterrows():
            lines.append(
                f"{r['Predictor']} & {r['B']} & {r['SE (HC3)']} & {r['t']} & {r['p']} & {r['95\\% CI']} \\\\"
            )
        lines.append("\\midrule")
        lines.append("\\multicolumn{6}{l}{\\textit{Panel B. Response-surface parameters (linear combinations)}} \\\\")
        lines.append("\\multicolumn{4}{l}{Parameter} & \\multicolumn{2}{r}{Estimate} \\\\")
        for _, r in surf_disp.iterrows():
            lines.append(f"\\multicolumn{{4}}{{l}}{{{r['Parameter']}}} & \\multicolumn{{2}}{{r}}{{{r['Estimate']}}} \\\\")
        lines.append("\\bottomrule")
        lines.append("\\end{tabular}")
        _write_tex(os.path.join(OUT_DIR, "tables", "table2_main_model_tabular.tex"), "\n".join(lines))

    # Table 3 (model comparison; compute additional metrics from modeling dataset if available)
    dfm_path = os.path.join(OUT_DIR, "modeling_dataset_with_predictions.csv")
    if os.path.exists(dfm_path):
        mdf = pd.read_csv(dfm_path)
        # Outcome column exists in pipeline
        y = pd.to_numeric(mdf.get("periop_intensity_index_z"), errors="coerce")
        yhat_b = pd.to_numeric(mdf.get("pci3_pred_baseline"), errors="coerce")
        yhat_f = pd.to_numeric(mdf.get("pci3_pred_full"), errors="coerce")

        def _r2(y_, yhat_):
            ok = y_.notna() & yhat_.notna()
            yy = y_[ok].astype(float).to_numpy()
            yh = yhat_[ok].astype(float).to_numpy()
            if yy.size == 0:
                return float("nan"), 0
            ssr = float(((yy - yh) ** 2).sum())
            sst = float(((yy - yy.mean()) ** 2).sum())
            return (1.0 - ssr / sst) if sst > 0 else float("nan"), int(yy.size)

        r2_b, n_b = _r2(y, yhat_b)
        r2_f, n_f = _r2(y, yhat_f)

        # k includes intercept
        k_b = 1 + len(model_res["baseline"]["predictors"])
        k_f = 1 + len(model_res["full_response_surface"]["predictors"])

        def _adj_r2(r2, n, k):
            if pd.isna(r2) or n <= k + 1:
                return float("nan")
            return 1.0 - (1.0 - r2) * (n - 1) / (n - k - 1)

        t3 = pd.DataFrame(
            [
                {
                    "Model": "Objective burden baseline",
                    "N": n_b,
                    "Predictors (k)": k_b,
                    "$R^2$": r2_b,
                    "Adj. $R^2$": _adj_r2(r2_b, n_b, k_b),
                },
                {
                    "Model": "Attachment response surface + covariates",
                    "N": n_f,
                    "Predictors (k)": k_f,
                    "$R^2$": r2_f,
                    "Adj. $R^2$": _adj_r2(r2_f, n_f, k_f),
                },
                {
                    "Model": "$\\Delta R^2$ (full - baseline)",
                    "N": "",
                    "Predictors (k)": "",
                    "$R^2$": r2_f - r2_b if (not pd.isna(r2_f) and not pd.isna(r2_b)) else float("nan"),
                    "Adj. $R^2$": "",
                },
            ]
        )
        t3_disp = t3.copy()
        t3_disp["$R^2$"] = t3_disp["$R^2$"].map(lambda x: _fmt_num(x, 3) if x != "" else "")
        t3_disp["Adj. $R^2$"] = t3_disp["Adj. $R^2$"].map(lambda x: _fmt_num(x, 3) if x != "" else "")
        t3_tex = t3_disp.to_latex(index=False, escape=False, column_format="lrrrr", caption=None, label=None)
        _write_tex(os.path.join(OUT_DIR, "tables", "table3_model_comparison_tabular.tex"), t3_tex)

    # Captions / blueprint
    write_md(
        os.path.join(OUT_DIR, "FIGURE_TABLE_CAPTIONS_pua.md"),
        f"""## Captions (exotic manuscript) — generated {now_iso()}

### Tables
- **Table 1. Sample characteristics and descriptives.** Descriptive statistics for attachment, covariates, PCI³ components, and the PCI³ index. Missingness is reported per variable.
- **Table 2. Main response-surface model (PCI³).** Robust HC3 OLS fallback estimates for anxiety/avoidance response surface plus covariates; includes surface parameters a1–a4.
- **Table 3. Incremental validity.** Baseline (objective burden only) vs attachment response-surface model comparison (ΔR² as fallback; use LOO/WAIC if Bayesian enabled).
- **Table 4. Secondary outcomes.** Response-surface effects on utilization_shortterm_z, pharmaburden_z, pain_burden_z, sedation_risk_z.

### Figures
- **Figure 1. Conceptual model (DAG).** Attachment insecurity (anxiety/avoidance) influences peri-intake care intensity (PCI³) beyond objective burden (CCI, surgical severity, oncology activity).
- **Figure 2. Response surface heatmap.** Predicted PCI³ over standardized anxiety × avoidance (covariates at median).
- **Figure 3. Perioperative Utilization Amplification (PUA).** Residual PCI³ after baseline objective burden model plotted against attachment insecurity.
- **Figure 4. Coefficient forest plot.** Main model coefficients with 95% CI (HC3).
""",
    )

    print("✓ Wrote Table 1 and caption file.")


if __name__ == "__main__":
    main()


