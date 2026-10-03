def propose_experiments(gene, primary_field, other_field, sub_field):
    # these are STUDY DESIGN TEMPLATES (not medical instructions)
    return [
        f"experiment 1 (triple-intersection pilot): identify 5 patients with {primary_field} + {other_field} comorbidity under {sub_field}-relevant treatment context; track pre/post markers; early-kill if no directional change in 2–4 weeks",
        f"experiment 2 (retrospective signal): query existing records/literature in {other_field} for {gene} associations under {sub_field}; early-kill if effect is null or contradictory",
        f"experiment 3 (biomarker correlation): measure {gene} proxy/marker vs clinical endpoints in {other_field} cohorts receiving {sub_field}-related interventions; early-kill if correlation < threshold",
        f"experiment 4 (mechanism proxy assay): run a cheap in vitro assay relevant to {other_field} with perturbation of {gene} under {sub_field}-like conditions; early-kill if no response vs control",
        f"experiment 5 (replication stress test): repeat the strongest assay with 2 independent datasets/conditions; early-kill if signal is not reproducible"
    ]
