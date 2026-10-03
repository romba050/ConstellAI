# src/stage6_experiment_proposal.py
from docx import Document
from src.stage4_compound_overlap import COMPOUND_DB

def generate_proposal(drug, selected_compounds, coverage, output_dir):
    doc = Document()
    doc.add_heading(f"Case Memo — Natural Mimic / Intersection of {drug} Axis", 0)
    
    doc.add_paragraph(f"Context: {drug}-relevant signaling")
    doc.add_paragraph(f"Natural stack: {', '.join(selected_compounds)}")
    doc.add_paragraph("Intent: mechanistic intersection + signature convergence, not clinical substitution")

    # 1) Anchor biology (now drug-specific)
    doc.add_heading("1) Anchor biology (targets → pathways)", level=1)
    if "Imatinib" in drug or "Erlotinib" in drug or "Sorafenib" in drug:
        doc.add_paragraph("• Primary RTKs: KIT, PDGFRA/PDGFRB (or EGFR for Erlotinib)")
    elif "Doxorubicin" in drug:
        doc.add_paragraph("• Primary: DNA intercalation, topoisomerase II inhibition, ROS generation")
    elif "Metformin" in drug:
        doc.add_paragraph("• Primary: AMPK activation, mTOR suppression, SIRT1/FOXO3")
    else:
        doc.add_paragraph("• Primary targets extracted from literature")
    doc.add_paragraph("• Downstream axes: PI3K/AKT, RAS/ERK, JAK/STAT, cell-cycle + survival programs")

    # 2) Natural compounds selected
    doc.add_heading("2) Natural compounds selected", level=1)
    for c in selected_compounds:
        data = COMPOUND_DB.get(c, {})
        p = doc.add_paragraph()
        p.add_run(c).bold = True
        doc.add_paragraph(f"• Evidence cluster: {data.get('evidence', 'N/A')}")
        doc.add_paragraph(f"• Role in stack: {data.get('role', 'N/A')}")

    # Why this stack / Hypothesis / Plan / Risk / Schema stay the same (already good)
    # ... (keep the rest of the file exactly as your previous version)

    # Save
    path = f"{output_dir}/{drug.lower().replace(' ', '_')}_case_memo.docx"
    doc.save(path)
    print(f"Rich case memo saved: {path}")