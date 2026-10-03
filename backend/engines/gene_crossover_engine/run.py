from core.pubmed import fetch_pubmed
from core.gene_extract import extract_genes
from core.memory import load, save
from core.propose import propose_experiments
from core.pdf_out import write_pdf
from core.evidence import paper_sentiment_score

EMAIL = "alexxc@live.se"
RETMAX = 500

OTHER_FIELDS = ["cardiology","neurology","metabolic","pulmonology","immunology"]

ANCHOR_MIN_POS_PAPERS = 3
CREEP_MAX_POS_PAPERS = 1

def count_positive_gene_mentions(papers):
    counts = {}
    for p in papers:
        s = paper_sentiment_score(p["title"], p["abstract"])
        if s <= 0:
            continue
        genes = extract_genes(p["abstract"])
        for g in genes:
            counts[g] = counts.get(g, 0) + 1
    return counts

def main():
    primary = input("primary field: ").strip().lower()
    sub = input("sub field: ").strip().lower()

    memory = load()

    anchor_papers = fetch_pubmed(primary, sub, EMAIL, RETMAX)
    anchor_counts = count_positive_gene_mentions(anchor_papers)

    key = f"{primary}+{sub}"
    for g, c in anchor_counts.items():
        memory.setdefault(g, {})[key] = c

    aggregated = {}

    for field in OTHER_FIELDS:
        creep_papers = fetch_pubmed(field, sub, EMAIL, RETMAX)
        creep_counts = count_positive_gene_mentions(creep_papers)

        for g, anchor_c in anchor_counts.items():
            if anchor_c < ANCHOR_MIN_POS_PAPERS:
                continue

            creep_c = creep_counts.get(g, 0)
            if creep_c <= CREEP_MAX_POS_PAPERS:
                entry = aggregated.setdefault(g, {
                    "gene": g,
                    "from": primary,
                    "anchor_pos_papers": anchor_c,
                    "targets": []
                })
                entry["targets"].append({
                    "field": field,
                    "creep_pos_papers": creep_c,
                    "score": round(anchor_c / (1 + creep_c), 2),
                    "experiments": propose_experiments(g, primary, field, sub)
                })

    save(memory)

    results = list(aggregated.values())
    results.sort(key=lambda x: x["anchor_pos_papers"], reverse=True)

    top = results[:5]
    for r in top:
        print(r)
        print()

    pdf_path = write_pdf(top, primary, sub)
    print(f"pdf written to {pdf_path}")
    print("done. good day.")

if __name__ == "__main__":
    main()
