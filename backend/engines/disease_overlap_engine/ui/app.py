import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import yaml
from engine.pipeline import pubmed_loader, mechanism_extractor, pathway_graph, crossover_engine, proposal_gate
from engine.reporting import explain


st.set_page_config(page_title="crossover engine v6", layout="wide")
st.title("crossover hypothesis engine v6 (llm-enabled)")

cfg = yaml.safe_load(open("config.yaml", "r", encoding="utf-8"))

c1, c2 = st.columns([1, 1])
with c1:
    cfg["mode"] = st.selectbox("mode", ["exploratory", "decision"], index=0)
    term = st.text_input("pubmed query", value=cfg["query"]["term"])
with c2:
    cfg["llm"]["enabled"] = st.toggle("use llm extraction", value=bool(cfg["llm"]["enabled"]))
    cfg["llm"]["provider"] = st.selectbox("llm provider", ["ollama", "llamacpp"], index=0)
    cfg["llm"]["model"] = st.text_input("llm model", value=cfg["llm"]["model"])

retmax = st.slider("retmax papers", 10, 200, int(cfg["sources"]["pubmed"]["retmax"]), 10)

if st.button("run"):
    with st.spinner("loading pubmed abstracts..."):
        papers = pubmed_loader.load(term, retmax=retmax)
    st.write({"papers": len(papers)})
    if papers:
        st.caption("sample abstract")
        st.code(papers[0][:1200])

    with st.spinner("extracting mechanisms (llm or fallback)..."):
        mechs = mechanism_extractor.extract(papers, cfg)
    st.write({"mechanisms": len(mechs)})
    if mechs:
        st.caption("sample mechanisms")
        st.json([m.model_dump() for m in mechs[:10]])

    with st.spinner("clustering pathways..."):
        mechs = pathway_graph.cluster(mechs)

    with st.spinner("finding cross-domain candidates..."):
        cands = crossover_engine.find(mechs, cfg)
    st.write({"candidates": len(cands)})
    if cands:
        st.caption("top candidates (raw)")
        st.json(cands[:5])

    with st.spinner("gating..."):
        results = proposal_gate.evaluate(cands, cfg)

    st.subheader("results (humanized)")
    st.json([explain.humanize(r, cfg) for r in results[:25]])
