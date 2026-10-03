from fpdf import FPDF
from datetime import date
import os
import textwrap

FONT_PATH = "core/fonts/DejaVuSans.ttf"
MAX_LINE_LEN = 90

class PDF(FPDF):
    pass

def safe_lines(text):
    return textwrap.wrap(text, MAX_LINE_LEN)

def write_pdf(results, primary, sub):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)

    if not os.path.exists(FONT_PATH):
        raise RuntimeError("Missing font: core/fonts/DejaVuSans.ttf")

    pdf.add_font("DejaVu", "", FONT_PATH, uni=True)
    pdf.set_font("DejaVu", size=10)

    pdf.cell(0, 8, "MED-R REAL PUBMED REPORT", ln=1)
    pdf.cell(0, 8, f"date: {date.today()}", ln=1)
    pdf.cell(0, 8, f"primary field: {primary}", ln=1)
    pdf.cell(0, 8, f"sub field: {sub}", ln=1)
    pdf.ln(6)

    for r in results:
        pdf.cell(0, 8, f"Gene: {r['gene']}", ln=1)
        pdf.cell(0, 8, f"Anchor positive papers: {r['anchor_pos_papers']}", ln=1)
        pdf.ln(2)

        for t in r["targets"]:
            pdf.cell(0, 8, f"Target field: {t['field']}", ln=1)
            pdf.cell(0, 8, f"Creep positive papers: {t['creep_pos_papers']}", ln=1)
            pdf.cell(0, 8, f"Score: {t['score']}", ln=1)
            pdf.ln(1)

            pdf.cell(0, 8, "Proposed experiments:", ln=1)
            for e in t["experiments"]:
                for line in safe_lines(f"- {e}"):
                    pdf.cell(0, 6, line, ln=1)
            pdf.ln(4)

        pdf.ln(6)

    os.makedirs("outputs", exist_ok=True)
    out = f"outputs/{primary}_{sub}_report.pdf"
    pdf.output(out)
    return out
