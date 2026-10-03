import argparse
import yaml
import os
from src.stage1_literature_aggregation import fetch_papers
from src.stage2_activation_extraction import extract_activations
from src.stage3_target_normalization import normalize_targets
from src.stage4_compound_overlap import find_overlapping_compounds
from src.stage5_coverage_optimization import optimize_combination
from src.stage6_experiment_proposal import generate_proposal

def main():
    parser = argparse.ArgumentParser(description="MEDR Pipeline - Oncology Drug to Natural Mimic")
    parser.add_argument("--drug", type=str, required=True, help="Name of the oncology drug (e.g. Imatinib, Metformin)")
    args = parser.parse_args()

    # Load config
    with open("config.yaml", "r") as f:
        cfg = yaml.safe_load(f)
    
    # Override drug from command line
    cfg["drug"] = args.drug

    print(f"=== MEDR Pipeline - {cfg['drug']} ===")

    # Stage 1: Fetch literature
    print("Fetching abstracts...")
    papers = fetch_papers(cfg["drug"], cfg["pubmed_email"], cfg["max_papers"])

    # Stage 2: Extract activation targets from abstracts
    print("Extracting targets...")
    activations = extract_activations(papers, cfg["min_frequency"])

    # Stage 3: Normalize targets (currently just pass-through)
    normalized = normalize_targets(activations)

    # Stage 4: Find overlapping natural compounds
    print("Finding compound overlaps...")
    compounds = find_overlapping_compounds(normalized)

    # Stage 5: Optimize minimal combination (pass drug name for class bonuses)
    print("Optimizing stack...")
    selected, coverage = optimize_combination(
        compounds, 
        normalized, 
        cfg.get("risk_threshold", 30), 
        cfg["drug"]  # <-- this enables drug-class specific bonuses
    )

    # Stage 6: Generate rich case memo
    print("Generating proposal...")
    output_dir = cfg["output_dir"]
    os.makedirs(output_dir, exist_ok=True)
    generate_proposal(cfg["drug"], selected, coverage, output_dir)

    print("Done! Check outputs in:", output_dir)
    if "downloads_path" in cfg:  # optional fallback
        print("Also check Downloads folder if OneDrive lock occurs.")

if __name__ == "__main__":
    main()