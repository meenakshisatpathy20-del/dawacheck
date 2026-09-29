"""Pipeline test on a synthetic PDF laid out like a CIB&RC 'Major Uses' table:
chemical heading above the table, two-row header, blank crop cells, several pests per row."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

pdfplumber = pytest.importorskip("pdfplumber")
reportlab = pytest.importorskip("reportlab")

from pipeline import extract_tables, parse_major_uses  # noqa: E402


def make_pdf(path: Path):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    style = TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)])
    header = [["Crop", "Common name of pest", "Dosage/ha", "", "Dilution in water (L)", "Waiting period (days)"],
              ["", "", "a.i. (g)", "Formulation (g/ml)", "", ""]]
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    h = getSampleStyleSheet()["Heading3"]
    story = [
        Paragraph("1. Imidacloprid 17.8% SL", h),
        Table(header + [["Cotton", "Jassids, Aphids & Thrips", "20-25", "100-125", "500-700", "40"],
                        ["", "Whitefly", "25", "125", "500-700", "40"],
                        ["Paddy", "BPH", "20-25", "100-125", "500", "40"]], style=style),
        Spacer(1, 20),
        Paragraph("2. Tricyclazole 75% WP", h),
        Table(header + [["Rice", "Blast", "225-300", "300-400", "500", "--"]], style=style),
    ]
    doc.build(story)


def test_parse_synthetic_major_uses(tmp_path):
    pdf = tmp_path / "major_uses_test.pdf"
    make_pdf(pdf)
    events = extract_tables.extract(pdf)
    claims, problems = parse_major_uses.parse(events, pdf.name)
    got = {(c["ai"], c["crop"], c["pests"][0]) for c in claims}
    assert got == {
        ("imidacloprid", "cotton", "jassid"), ("imidacloprid", "cotton", "aphid"), ("imidacloprid", "cotton", "thrips"),
        ("imidacloprid", "cotton", "whitefly"), ("imidacloprid", "rice", "brown plant hopper"),
        ("tricyclazole", "rice", "blast"),
    }
    jassid = next(c for c in claims if c["pests"] == ["jassid"])
    assert jassid["form_ha"] == "100-125" and jassid["phi_days"] == 40 and jassid["page"] == 1
    assert jassid["unit"] == "ml" and jassid["water_l_ha"] == 500
    blast = next(c for c in claims if c["ai"] == "tricyclazole")
    assert blast["phi_days"] is None and blast["unit"] == "g"
    assert not problems
    review = parse_major_uses.validate(claims)
    assert review == []
