
crossover hypothesis engine v6 (llm-enabled)
===========================================

this is a mechanism-first, cross-domain hypothesis prioritization engine.

v6 adds
------
- llm-based extraction + normalization (meta llama 3.1 8b instruct via local ollama or llama.cpp server)
- explicit modes: exploratory vs decision
- pathway clustering (energy-sensing axis + extendable graph)
- explainable outputs (why proposed / why rejected)
- streamlit ui

quick start (windows)
---------------------
1) unzip, open terminal in folder
2) python -m venv venv
3) venv\Scripts\activate
4) pip install -r requirements.txt

run cli:
  python run_engine.py

run ui:
  streamlit run ui/app.py

llm setup (recommended: ollama)
------------------------------
install ollama, then pull a llama 3.1 8b instruct model (name depends on your ollama build).
examples:
  ollama pull llama3.1:8b
  ollama pull llama3.1:8b-instruct   (if available)

set in config.yaml:
  llm:
    provider: ollama
    model: llama3.1:8b

notes
-----
- if llm is unavailable, the engine falls back to a conservative regex extractor (lower quality).
- pubmed ingestion uses medline abstracts (stable).
