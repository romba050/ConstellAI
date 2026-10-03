import os
from data_sources.pubmed_fetcher import fetch_pubmed_data
from data_sources.forum_scraper import fetch_forum_posts
from llm.llama_client import ask_llm
from report.pdf_builder import build_pdf


MAX_CHUNK_CHARS = 6000  # safe for 4k context


def chunk_text(text, max_chars):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]


def summarize_pubmed(compound, pubmed_raw):

    chunks = chunk_text(pubmed_raw, MAX_CHUNK_CHARS)

    partial_summaries = []

    for i, chunk in enumerate(chunks):
        print(f"Summarizing chunk {i+1}/{len(chunks)}")

        prompt = f"""
Summarize the following PubMed abstracts about {compound}.
Extract only:
- mechanisms
- biomarker changes
- human vs animal data
- dosage ranges
- safety findings
Keep concise bullet format.

{chunk}
"""
        summary = ask_llm(prompt)
        partial_summaries.append(summary)

    combined = "\n\n".join(partial_summaries)

    final_prompt = f"""
Combine the following summaries into one clean structured
Objective Evidence section about {compound}.

Organize into:
1. Mechanisms
2. Human Data
3. Animal Data
4. Biomarker Effects
5. Dosage Patterns
6. Safety Profile

{combined}
"""

    return ask_llm(final_prompt)


def generate_report(compound):

    print("Fetching PubMed data...")
    pubmed_raw = fetch_pubmed_data(compound)

    print("Fetching forum data...")
    forum_raw = fetch_forum_posts(compound)

    print("Analyzing objective evidence...")
    objective_summary = summarize_pubmed(compound, pubmed_raw)

    print("Analyzing subjective reports...")
    subjective_prompt = f"""
Analyze the following forum discussions about {compound}.
Extract:
- common positive experiences
- common side effects
- time to effect
- contradictions
Return structured summary.

{forum_raw}
"""

    subjective_summary = ask_llm(subjective_prompt)

    os.makedirs("outputs", exist_ok=True)
    filename = f"outputs/{compound}_report.pdf"

    build_pdf(filename, objective_summary, subjective_summary)

    print(f"Report generated: {filename}")


if __name__ == "__main__":
    compound = input("Enter compound/supplement name: ")
    generate_report(compound)
