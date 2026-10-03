import re

GENE_RE = re.compile(r"\b[A-Z][A-Z0-9]{2,6}\b")
MUTATION = re.compile(r"^[A-Z]\d+[A-Z]$")

STOPWORDS = {
    # logic / language
    "AND", "OR", "NOT",

    # trial phases / numerals
    "I", "II", "III", "IV",

    # datasets / metrics
    "TCGA", "AUC", "ROC", "HR", "CI",

    # endpoints / biomarkers
    "TMB", "PFS", "OS", "DFS", "ORR",

    # biology but not genes
    "TME", "ECM", "CAF",

    # therapies
    "ICI", "CAR", "ADC",

    # molecules
    "ATP", "ADP", "AMP", "NAD", "NADH", "NADPH",

    # generic bio
    "DNA", "RNA", "MRNA", "CDNA",

    # diseases
    "HCC", "GIST", "AML", "ALL", "CML", "NSCLC", "SCLC",
}

NORMALIZE = {
    "CD117": "KIT",
    "DOG1": "ANO1",
}

def extract_genes(text):
    raw = set(GENE_RE.findall(text))
    genes = set()

    for t in raw:
        if t in STOPWORDS:
            continue
        if MUTATION.match(t):
            continue
        if sum(c.isdigit() for c in t) > sum(c.isalpha() for c in t):
            continue

        g = NORMALIZE.get(t, t)

        if sum(c.isalpha() for c in g) < 3:
            continue

        genes.add(g)

    return genes
