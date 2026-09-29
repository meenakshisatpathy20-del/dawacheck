# Mapping to the evaluation criteria (playbook section 16)

| Criterion | What proves it | Where in this repo |
|---|---|---|
| Innovation & Originality | No brand-neutral pesticide verifier found; Cocktail Checker, MRL Passport, Doctor Card, Fake-Batch Radar | `backend/app/services/{mix,spray,sos,radar}.py`; slide 6 |
| Problem Relevance | Government and peer-reviewed numbers, each with its source and year | `docs/DATA_SOURCES.md`; slides 2–3 |
| Technical Excellence | Knowledge base built from raw PDFs, deterministic engine with cited rules, measured OCR accuracy | `pipeline/`, `backend/app/rules/`, `scripts/accuracy_report.py`, 99 tests |
| Solution Design | AI reads, rules decide; one engine powers six features | `rules/rules.json` + `rules/engine.py`; slide 7 |
| User Experience | Voice in regional languages, three taps to a verdict, colour + icon + sound, one decision per screen | `frontend/src/farmer/`; `docs/deck/screens/` |
| Scalability | Add a crop = load its rows; add a state ban = one row (admin screen, effective dates); Docker deploy; OCR queue; PostGIS | `docker-compose.yml`, `backend/app/admin.py`, `backend/app/jobs.py`, `backend/app/geo.py` |
| Feasibility | All data public; working demo; 36-hour plan | `docs/DEMO_SCRIPT.md`, `docs/CHECKLIST.md` |
| Business Potential | Four paying segments, impact metrics built into the dashboard | `docs/BUSINESS.md`; `/metrics`; Impact tab |
| Social Impact | Farmer health (SOS, gear), farmer money (Bill Scan), food safety (PHI), export income (MRL Passport) | slide 9 |
| Presentation & Demonstration | Live scans on real packs, backup video, 3-minute script | `docs/DEMO_SCRIPT.md`, `docs/DawaCheck_pitch.pptx` |
| Team Collaboration | Clear roles, shared repo and task board | playbook section 13; this repository |
