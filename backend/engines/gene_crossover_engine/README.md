
MED-R v1 — REAL PUBMED + GENE MEMORY (HARD-FAIL)

GOAL
- architecture-only research triage engine
- NO fake / stub data
- pubmed must succeed or pipeline stops

WHAT IT DOES
- user inputs:
  - primary field (e.g. oncology)
  - sub field (e.g. immunotherapy)
- pulls ALL matching PubMed papers
- extracts genes
- stores gene ↔ field memory
- proposes novel crossover experiments
- outputs ranked PDF

RUN
pip install -r requirements.txt
python run.py

NOTE
Decision-support only. Not medical advice.
