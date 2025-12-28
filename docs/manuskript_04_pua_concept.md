---
title: "Perioperative Utilization Amplification (PUA): Attachment–Utilization Amplification in the peri-intake window"
shorttitle: "PUA in head and neck oncology"
date: "2025-12-28"
keywords:
  - attachment insecurity
  - healthcare utilization
  - perioperative care
  - psycho-oncology
  - response surface analysis
---

## 1) Paper concept (publishable + “exotic”)

### Core idea
Instead of asking only “attachment insecurity → more utilization”, we define a clinically interpretable construct:

- **Perioperative Utilization Amplification (PUA)**: the *excess* peri-intake care/intervention intensity beyond what would be expected from objective disease burden and care complexity.

This maps onto the reviewer-facing clinical question:
“Who *needs* more (objective burden), and who *draws* more intensity beyond objective burden (amplification)?”

### Constructs (operational)

#### (A) Exposure: Attachment (ECR-RD12)
- **Attachment anxiety**: `ecr_anxiety_mean_0_4` (0–4)
- **Attachment avoidance**: `ecr_avoidance_mean_0_4` (0–4)

Optional derived:
- `attachment_insecurity_mean_0_4 = mean(ecr_anxiety_mean_0_4, ecr_avoidance_mean_0_4)`
- `attachment_asymmetry_anx_minus_avoid = ecr_anxiety_mean_0_4 - ecr_avoidance_mean_0_4`

#### (B) Objective controls (core)
- `CCI_altersadjustiert` (age-adjusted Charlson Comorbidity Index)
- `OP_Schweregrad_plus30_Hoechster` (highest surgical severity in +30d; 0–5)
- `oncology_activity_z` (z-composite of oncology activity)
- plus demographics: `age`, `sex_bin`

#### (C) Primary outcome index: PCI³
Define a single high-signal primary outcome:

- **PCI³ = Perioperative Care & Intervention Intensity Index** (z-scale)

Proposed components (already in your dataset):
- `utilization_shortterm_z` (short-term contact intensity)
- `pharmaburden_z` (pharmacotherapy burden proxy)
- `pain_burden_z` (pain burden proxy)
- `sedation_risk_z` (sedation exposure proxy)

Optional add-on if present:
- `lab_postop_z = z(log1p(lab_postop_Anzahl))`

Define:
- `periop_intensity_index_z = mean(utilization_shortterm_z, pharmaburden_z, pain_burden_z, sedation_risk_z[, lab_postop_z])`

Internal checks:
- component correlations; internal consistency (α/ω); leave-one-out sensitivity.

#### (D) Amplification: PUA residual
PUA is the residual intensity after objective burden:

Baseline model:

\[
\widehat{PCI^3} = f(\text{CCI}, \text{OP severity}, \text{oncology activity}, \text{age}, \text{sex})
\]

Define:
- `PUA_residual = periop_intensity_index_z - predicted_baseline`

Interpretation:
- Positive PUA: “more intensity than expected”
- Negative PUA: “less intensity than expected”

## 2) Hypotheses (confirmatory) + exploratory boundary

### Confirmatory hypotheses
- **H1 (Amplification):** Higher attachment insecurity predicts higher PCI³, controlling for objective burden (`CCI_altersadjustiert`, `OP_Schweregrad_plus30_Hoechster`, `oncology_activity_z`) and demographics.
- **H2 (Style-specific / non-linear):** Effects depend on the combination of anxiety and avoidance (response-surface logic):
  - “Fearful” (high anxiety + high avoidance) → highest predicted PCI³/PUA
  - “Anxious” (high anxiety, low avoidance) → increased contact/monitoring
  - “Avoidant” (high avoidance, low anxiety) → fewer planned contacts but possible escalation patterns on medication proxies (outcome-dependent)

### Explicit exploratory extension
Exploratory analyses are clearly separated:
- pain documentation frequency vs pain intensity (NRS mean/max) vs medication administration
- distribution-aware count models (hurdle/ZINB) if raw counts are used

## 3) Statistical design (high-sophisticated but feasible at N≈97)

### Main model: Response surface regression
Standardize predictors: `anx_z`, `avoid_z`, `cci_z`, `opsev_z`, `onco_z`, `age_z`.

Model:
- `periop_intensity_index_z ~ anx_z + avoid_z + anx_z^2 + anx_z:avoid_z + avoid_z^2 + cci_z + opsev_z + onco_z + age_z + sex_bin`

Robustness:
- Student-t errors (Bayesian) if available; otherwise robust SE / Huber.

Surface parameters (report with intervals):
- \(a_1 = b_1 + b_2\): slope along congruence line (anx=avoid)
- \(a_2 = b_3 + b_4 + b_5\): curvature along congruence line
- \(a_3 = b_1 - b_2\): slope along incongruence line (anx=-avoid)
- \(a_4 = b_3 - b_4 + b_5\): curvature along incongruence line

### Incremental validity
Baseline model (objective burden only):
- `periop_intensity_index_z ~ cci_z + opsev_z + onco_z + age_z + sex_bin`

Compare baseline vs attachment model using:
- Bayesian: LOO-CV ΔELPD (or WAIC), Bayes R²
- fallback: ΔR² + 10-fold CV RMSE difference

### Secondary outcomes
Run the same response-surface model per outcome:
- `utilization_shortterm_z`, `pharmaburden_z`, `pain_burden_z`, `sedation_risk_z`

Optionally switch to NB/ZINB/hurdle if using raw counts with many zeros.

## 4) Figure blueprints (“high-end”)

1. **Figure 1 (DAG / Concept):** Attachment (anx/avoid) → PCI³ / PUA. Controls: CCI, OP severity, oncology activity.
2. **Figure 2 (Response surface heatmap):** X=anx_z, Y=avoid_z, color=predicted PCI³ (covariates at median). Mark quadrants (secure/anxious/avoidant/fearful).
3. **Figure 3 (PUA residual):** PUA_residual vs attachment insecurity; optionally 2D plane or quartiles (no median split inference).
4. **Figure 4 (Forest):** standardized effects (main model) including quadratic + interaction; intervals.
5. **Figure 5 (Outcome panel):** small multiples of effects on each outcome.

## 5) Table shells (journal-ready)

- **Table 1:** sample + missingness (M/SD/Median/IQR)
- **Table 2:** main model + surface parameters a1–a4
- **Table 3:** model comparison (baseline vs attachment): ΔELPD/ΔR², calibration
- **Table 4:** secondary outcomes (compact)

## 6) Results text templates (fill with real numbers)

### Primary model (template)
In a response-surface model controlling for objective burden (CCI, surgical severity, oncology activity) and demographics, attachment insecurity contributed to peri-intake care and intervention intensity (PCI³). The effect was not purely additive: curvature parameters indicated that specific anxiety–avoidance combinations were associated with disproportionate intensity, consistent with an “amplification” pattern. The attachment model improved predictive performance relative to the objective-burden baseline model (ΔELPD/ΔR²).

### Clinical meaning (template)
Clinically, PUA suggests that part of short-term peri-intake intensity is not explained by objective burden alone, but by interpersonal regulation styles that become salient under threat. Attachment-informed screening could help identify patients at risk for amplified intensity in the perioperative window, enabling targeted expectation management, structured communication, and early psychosocial co-interventions.


