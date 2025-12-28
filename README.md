# 04_exotic_manis — Perioperative Utilization Amplification (PUA)

This folder contains a publishable “exotic” paper concept and a reproducible analysis scaffold:

- `docs/manuskript_04_pua_concept.md`: the paper concept (PUA / PCI³), hypotheses, variable definitions (with real variable names), analysis pipeline, figure/table blueprints, and ready-to-use result text templates.
- `prompts/cursor_ai_prompt_blocks.md`: copy/paste-ready prompt blocks for Cursor AI.
- `prompts/euros_ai_prompt_blocks.md`: copy/paste-ready prompt blocks for “EUROS AI” (medical writing).
- `code/`: reproducible scripts (prep/models/figures/tables) that write to `outputs_pua/`.
- `outputs_pua/`: generated tables, figures, and text snippets.

## Primary dataset
Expected input (adjust if you prefer a different file):
- `/home/jbs123/Dokumente/intake/MAJOR_T1_NUMERIC_ONLY_SCORES_HADS_FBK_LPFS_ECR_IMPUTED_GENERALKONSENT_J_ONLY.xlsx`

## Quick run
From `/home/jbs123/Dokumente/intake`:

```bash
python3 04_exotic_manis/code/01_prep.py
python3 04_exotic_manis/code/02_models.py
python3 04_exotic_manis/code/03_figures.py
python3 04_exotic_manis/code/04_tables_and_snippets.py
```


