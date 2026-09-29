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


def _pdf_with(path: Path, story_fn):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate
    SimpleDocTemplate(str(path), pagesize=A4).build(story_fn())


def test_parse_registered_products(tmp_path):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    from pipeline import parse_registry

    grid = TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)])
    pdf = tmp_path / "registered.pdf"
    _pdf_with(pdf, lambda: [Table([
        ["S. No.", "Name of Pesticide", "Registration No.", "Name of the Registrant", "Brand name"],
        ["1", "Imidacloprid 17.8% SL", "CIR-111/2019", "Example Agro Ltd", "Examplo"],
        ["2", "Tricyclazole 75% WP", "CIR-222/2020", "Sample Chem", ""],
    ], style=grid)])
    rows = parse_registry.parse_registered(extract_tables.extract(pdf), pdf.name)
    assert [(r["ai"], r["pct"], r["type"], r["reg_no"]) for r in rows] == [
        ("imidacloprid", 17.8, "SL", "CIR-111/2019"), ("tricyclazole", 75.0, "WP", "CIR-222/2020")]
    assert rows[0]["brand"] == "Examplo" and rows[1]["brand"] is None


def test_parse_banned_list(tmp_path):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, Table, TableStyle
    from pipeline import parse_registry

    grid = TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)])
    h = getSampleStyleSheet()["Heading3"]
    pdf = tmp_path / "banned.pdf"
    _pdf_with(pdf, lambda: [
        Paragraph("A. Pesticides banned for manufacture, import and use", h),
        Table([["S. No.", "Name of Pesticide"], ["1", "Endosulfan"], ["2", "Phorate"]], style=grid),
        Paragraph("B. Pesticides restricted for use in the country", h),
        Table([["S. No.", "Name of Pesticide", "Restriction"], ["1", "Monocrotophos", "Not for use on vegetables"]], style=grid),
    ])
    rows = parse_registry.parse_banned(extract_tables.extract(pdf), pdf.name)
    assert [(r["name"], r["status"]) for r in rows] == [
        ("endosulfan", "banned"), ("phorate", "banned"), ("monocrotophos", "restricted")]
    assert rows[2]["note"] == "Not for use on vegetables"


def test_import_eu_mrl(tmp_path):
    import json
    from pipeline import import_eu_mrl

    csv_path = tmp_path / "eu.csv"
    csv_path.write_text("Pesticide residue,Product,MRL (mg/kg)\n"
                        "Tricyclazole,Rice,0.01*\nBuprofezin,Rice,0.01*\nAzoxystrobin,Rice,5\n"
                        "Imidacloprid,Tomatoes,0.5\nChlorpyrifos,Tomatoes,0.01*\n")
    rows = import_eu_mrl.parse(csv_path)
    assert {(r["crop"], r["ai"]) for r in rows} == {("rice", "tricyclazole"), ("rice", "buprofezin"),
                                                    ("tomato", "chlorpyrifos")}
    flags = tmp_path / "flags.json"
    flags.write_text(json.dumps({"items": [{"crop": "rice", "market": "EU", "ai": "tricyclazole", "note": "x"}]}))
    assert import_eu_mrl.merge(rows, flags) == {"added": 2, "total": 3}
