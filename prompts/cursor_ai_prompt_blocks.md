### COPY/PASTE — CURSOR AI (full pipeline)

ROLE: You are a Senior Biostatistician + Research Software Engineer (Python-first) focused on robust, publishable analyses (N≈97), fully reproducible, with tables/figures and manuscript-ready text snippets.

GOAL / RESEARCH QUESTION:
Does attachment insecurity (ECR-RD12: `ecr_anxiety_mean_0_4`, `ecr_avoidance_mean_0_4`) predict higher short-term perioperative care and intervention intensity beyond objective disease burden (`CCI_altersadjustiert`), surgical severity (`OP_Schweregrad_plus30_Hoechster`), and oncology activity (`oncology_activity_z`)?

DATA:
- Primary Excel: `/home/jbs123/Dokumente/intake/MAJOR_T1_NUMERIC_ONLY_SCORES_HADS_FBK_LPFS_ECR_IMPUTED_GENERALKONSENT_J_ONLY.xlsx`
- Expected N ~ 96–97.

REQUIRED VARIABLES (minimum):
- Exposure: `ecr_anxiety_mean_0_4`, `ecr_avoidance_mean_0_4`
- Core covariates: `CCI_altersadjustiert`, `OP_Schweregrad_plus30_Hoechster`, `oncology_activity_z`, `sex_bin`, `age`
- Outcomes/components: `utilization_shortterm_z`, `pharmaburden_z`, `pain_burden_z`, `sedation_risk_z`
- Optional: `lab_postop_Anzahl` (if present)

TASKS (implement exactly; write outputs into `04_exotic_manis/outputs_exotic/`):

(1) DATA AUDIT & PREP
- Check columns, types, missingness; create a data dictionary.
- Standardize/encode: `sex_bin` as 0/1; create `age` if needed.
- Create z versions: `anx_z`, `avoid_z`, `cci_z`, `opsev_z`, `onco_z`, `age_z`.
- If `utilization_shortterm_z` etc. are missing, compute them using:
  - `utilization_shortterm_z = mean(z(log1p(konsultationen_plus7_Anzahl)), z(log1p(konsultationen_plus14_Anzahl)))`
  - `pharmaburden_z = mean(z(log1p(kisim_medi_distinct_atc)), z(log1p(kisim_medi_n)))`
  - `pain_burden_z = mean(z(log1p(szerf_postop_Anzahl)), z(log1p(schmerz_meds_ab_op_plus7_Anzahl)), z(log1p(meds_plus7_Anzahl_Opiate)))`
  - `sedation_risk_z = mean(z(meds_plus7_Anzahl_Benzodiazepin_ZDerivat), z(meds_plus7_Anzahl_Opiate))`

(2) PRIMARY INDEX (PCI³)
- Define `periop_intensity_index_z` = mean of:
  `utilization_shortterm_z`, `pharmaburden_z`, `pain_burden_z`, `sedation_risk_z`,
  plus optional `lab_postop_z = z(log1p(lab_postop_Anzahl))` if available.
- Report internal consistency (alpha + omega) and inter-component correlations.
- Sensitivity: recompute index leaving-one-component-out.

(3) UTILIZATION AMPLIFICATION (PUA)
- Fit baseline model WITHOUT attachment:
  `periop_intensity_index_z ~ cci_z + opsev_z + onco_z + age_z + sex_bin`
- Define `PUA_residual = observed - predicted_baseline`.

(4) MAIN MODEL: RESPONSE SURFACE (robust)
- Prefer Bayesian Student-t model if available; otherwise robust OLS:
  `periop_intensity_index_z ~ anx_z + avoid_z + anx_z^2 + anx_z:avoid_z + avoid_z^2 + cci_z + opsev_z + onco_z + age_z + sex_bin`
- Report coefficients, 95% intervals, and effect probabilities (Bayes) or p-values (fallback).
- Compute “surface parameters”:
  a1 = b1+b2 (slope congruence line anx=avoid)
  a2 = b3+b4+b5 (curvature congruence line)
  a3 = b1-b2 (slope incongruence anx=-avoid)
  a4 = b3-b4+b5 (curvature incongruence)

(5) INCREMENTAL VALIDITY
- Compare baseline vs attachment model:
  - If Bayes: LOO-CV ΔELPD + SE, Bayes R²
  - If frequentist fallback: ΔR², AIC/BIC, 10-fold CV RMSE difference

(6) SECONDARY OUTCOMES
- Repeat models for:
  `utilization_shortterm_z`, `pharmaburden_z`, `pain_burden_z`, `sedation_risk_z`
- Use distribution-aware models if raw counts exist (NB/ZINB/hurdle), otherwise same approach.

(7) FIGURES (export PNG + PDF)
- Fig1: conceptual DAG (Attachment → PUA/PCI³; controls: CCI/OP/Onco).
- Fig2: response-surface heatmap for predicted PCI³ over (anx_z, avoid_z), covariates at median.
- Fig3: PUA residual plot (PUA_residual vs attachment insecurity; plus 2D plane if possible).
- Fig4: forest plot of standardized coefficients.
- Fig5: small-multiples: effects on secondary outcomes.

(8) TABLES (CSV + LaTeX-ready)
- Table1: descriptive + missingness.
- Table2: main model + surface parameters (a1–a4).
- Table3: model comparison (baseline vs attachment).
- Table4: secondary models.

(9) MANUSCRIPT SNIPPETS
- Write `results_snippets.md` with 4 paragraphs:
  Primary model; incremental value; sensitivity; clinical interpretation.
- Write `analysis_log.md` documenting all transformations and model choices.

IMPORTANT:
- Reproducibility: fixed random seed.
- No median splits except for visualization.
- Use real variable names as above.


