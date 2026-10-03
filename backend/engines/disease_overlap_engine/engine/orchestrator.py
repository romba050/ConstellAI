
import yaml
from engine.pipeline import pubmed_loader, mechanism_extractor, pathway_graph, crossover_engine, proposal_gate
from engine.reporting import explain

def run():
    cfg = yaml.safe_load(open("config.yaml", "r", encoding="utf-8"))
    term = cfg["query"]["term"]
    retmax = cfg["sources"]["pubmed"]["retmax"]

    print("query:", term)
    papers = pubmed_loader.load(term, retmax=retmax)
    print("papers:", len(papers))

    mechs = mechanism_extractor.extract(papers, cfg)
    print("mechanisms:", len(mechs))

    mechs = pathway_graph.cluster(mechs)
    cands = crossover_engine.find(mechs, cfg)
    print("candidates:", len(cands))

    results = proposal_gate.evaluate(cands, cfg)
    print("results:", len(results))
    for r in results:
        print(explain.humanize(r, cfg))
