import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from utils import OUT_DIR, ensure_dirs


def savefig(path):
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()


def main():
    ensure_dirs()
    df = pd.read_csv(os.path.join(OUT_DIR, "modeling_dataset_with_predictions.csv"))

    fig_dir = os.path.join(OUT_DIR, "figures")

    # Figure 2: response-surface heatmap (predicted PCI³)
    # Build grid over anx_z/avoid_z; hold covariates at median; use fitted betas from table2
    coeffs = pd.read_csv(os.path.join(OUT_DIR, "tables", "table2_main_model_coeffs.csv"))
    b = dict(zip(coeffs["term"], coeffs["B"]))

    covar_terms = [t for t in b.keys() if t not in ("Intercept", "anx_z", "avoid_z", "anx2", "anx_x_avoid", "avoid2")]
    covar_medians = {c: float(df[c].median()) for c in covar_terms if c in df.columns}

    grid = np.linspace(-2.5, 2.5, 120)
    anx, avoid = np.meshgrid(grid, grid)
    pred = (
        b.get("Intercept", 0)
        + b.get("anx_z", 0) * anx
        + b.get("avoid_z", 0) * avoid
        + b.get("anx2", 0) * (anx ** 2)
        + b.get("anx_x_avoid", 0) * (anx * avoid)
        + b.get("avoid2", 0) * (avoid ** 2)
    )
    for c, m in covar_medians.items():
        pred += b.get(c, 0) * m

    plt.figure(figsize=(7.5, 6.5))
    im = plt.imshow(
        pred,
        origin="lower",
        extent=[grid.min(), grid.max(), grid.min(), grid.max()],
        aspect="auto",
        cmap="RdYlBu_r",
    )
    plt.colorbar(im, label="Predicted PCI³ (periop_intensity_index_z)")
    plt.xlabel("Attachment anxiety (anx_z)")
    plt.ylabel("Attachment avoidance (avoid_z)")
    # Title intentionally avoids hard-coded figure numbers (handled by manuscript captions).
    plt.title("Response surface: predicted PCI³ over anxiety × avoidance\n(covariates held at median)")
    savefig(os.path.join(fig_dir, "figure2_response_surface_heatmap.png"))

    # Figure 3: PUA residual vs attachment insecurity mean
    if "ecr_anxiety_mean_0_4" in df.columns and "ecr_avoidance_mean_0_4" in df.columns:
        df["attachment_insecurity_mean_0_4"] = (df["ecr_anxiety_mean_0_4"] + df["ecr_avoidance_mean_0_4"]) / 2.0

    if "PUA_residual" in df.columns and "attachment_insecurity_mean_0_4" in df.columns:
        plt.figure(figsize=(7.5, 5.5))
        plt.scatter(df["attachment_insecurity_mean_0_4"], df["PUA_residual"], alpha=0.75)
        plt.axhline(0, color="black", linewidth=1)
        plt.xlabel("Attachment insecurity (mean of anxiety/avoidance; 0–4)")
        plt.ylabel("PUA residual (observed PCI³ − predicted baseline)")
        plt.title("Perioperative Utilization Amplification (PUA) vs attachment insecurity")
        savefig(os.path.join(fig_dir, "figure3_pua_residual_scatter.png"))

    # Figure 4: Forest plot of standardized-ish coefficients (all predictors are z-scaled except sex)
    terms = [t for t in coeffs["term"].tolist() if t != "Intercept"]
    B = coeffs.set_index("term").loc[terms, "B"].to_numpy()
    SE = coeffs.set_index("term").loc[terms, "SE_HC3"].to_numpy()
    lo = B - 1.96 * SE
    hi = B + 1.96 * SE

    plt.figure(figsize=(10, 6.5))
    y = np.arange(len(terms))[::-1]
    plt.hlines(y, lo, hi, color="#2c3e50", linewidth=2)
    plt.plot(B, y, "o", color="#e74c3c")
    plt.axvline(0, color="black", linewidth=1)
    plt.yticks(y, terms)
    plt.xlabel("B (unstandardized; outcome is z-scaled)")
    plt.title("Main model coefficients (HC3; 95% CI)")
    savefig(os.path.join(fig_dir, "figure4_forest_main_model.png"))

    print("✓ Figures written to:", fig_dir)


if __name__ == "__main__":
    main()


