# rare_disease_mimic_engine

Purpose:
- Prototype engine for “rare disease → gene set → candidate drugs/compounds overlap”
- Provides “utfall” (english: spillover / off-target) genes for any selected list
- Provides a greedy “best bundle” optimizer (cover genes, minimize spillover)

Notes:
- This is a starter engine with registry-backed starter data.
- Later you can swap the registry-backed starter loaders with:
  - Open Targets disease→targets
  - ChEMBL drug→targets
  - Your drug-mimic engine outputs (drug→signed targets)
  - Natural compound DB (compound→targets)
