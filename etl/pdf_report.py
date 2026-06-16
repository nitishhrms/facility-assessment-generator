"""PDF output — renders the report model to an executive-ready PDF (Python).

Uses fpdf2 (pure-Python, no system dependencies). Mirrors the JS PDF: a fixed
INFINITE / MEDELITE branding banner, a two-column table, the QA summary, and a
clickable Medicare Care Compare source link.
"""

from pathlib import Path

from fpdf import FPDF

INK = (17, 24, 39)
ACCENT = (0, 113, 227)
SUBTLE = (107, 114, 128)


def generate_pdf(report: dict, dq: dict, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Branding banner (static — never overwritten by facility name).
    pdf.set_fill_color(*INK)
    pdf.rect(0, 0, 210, 18, style="F")
    pdf.set_xy(12, 5)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "INFINITE  -  Managed by MEDELITE")
    if report.get("state"):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_xy(150, 6)
        pdf.cell(48, 6, f"State: {report['state']}", align="R")

    # Title.
    pdf.set_xy(12, 26)
    pdf.set_text_color(*INK)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 9, "Facility Assessment Report", new_x="LMARGIN", new_y="NEXT")

    # QA summary.
    pdf.set_x(12)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*ACCENT)
    pdf.multi_cell(186, 6, f"QA Summary: {report.get('qa_summary', '')}")
    if dq:
        pdf.set_x(12)
        pdf.set_text_color(*SUBTLE)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(
            186, 5,
            f"Data quality: {dq['completeness']}% complete "
            f"({dq['populated']}/{dq['total']} CMS fields), "
            f"freshness {dq.get('processing_date') or 'n/a'}, status {dq['status']}.",
        )
    pdf.ln(2)

    # Two-column table.
    pdf.set_font("Helvetica", "", 10)
    for label, value in report["table_rows"]:
        y0 = pdf.get_y()
        pdf.set_x(12)
        pdf.set_text_color(*SUBTLE)
        pdf.multi_cell(78, 7, str(label), border=0)
        pdf.set_xy(92, y0)
        pdf.set_text_color(*INK)
        pdf.multi_cell(106, 7, str(value), border=0)

    # Clickable Medicare source link.
    pdf.ln(3)
    pdf.set_x(12)
    pdf.set_text_color(*ACCENT)
    pdf.set_font("Helvetica", "U", 10)
    pdf.cell(0, 7, "View on Medicare Care Compare", link=report["medicare_url"])

    pdf.output(str(out_path))
    return out_path
