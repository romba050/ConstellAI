from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

def build_pdf(filename, objective_text, subjective_text):
    doc = SimpleDocTemplate(filename)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>Objective Evidence</b>", styles["Heading1"]))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(objective_text.replace("\n", "<br/>"), styles["Normal"]))

    elements.append(Spacer(1, 0.8 * inch))
    elements.append(Paragraph("<b>Subjective Reports</b>", styles["Heading1"]))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(subjective_text.replace("\n", "<br/>"), styles["Normal"]))

    doc.build(elements)
