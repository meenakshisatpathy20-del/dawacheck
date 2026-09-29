# Risks, limitations and ethics (playbook section 18)

| Risk | Impact | Mitigation | Built as |
|---|---|---|---|
| App cannot prove a product is fake | False sense of safety or false accusation | Wording: "not in registry", "reported by farmers"; route to agriculture department and lab testing | No message ever says "fake"; radar note "reasons to inspect, not proof"; test asserts it |
| CIB&RC PDFs are messy and change | Wrong or missing label claims | Source file + page on every row; 30-question test set; re-parse each edition | `pipeline/`, `review.csv`, `backend/data/kb_questions.json`, `test_kb_questions.py` |
| OCR errors on worn or glossy packs | Wrong product identified | Farmer confirms product; low-confidence fields asked again; QR preferred | Confirm screen with pack photo, per-field photo crops, editable fields; strength/form cross-check; live QR detection |
| Brand → ingredient catalogue incomplete | Unknown products show as "not found" | Separate verdict: "not in our catalogue yet" (grey) vs "not in registry" (red); crowd-add with photo review | Rule G1; "Add this product" with photo; admin review queue |
| Tank-mix science is limited | Over-claiming | Check only duplicates, resistance group, toxicity; say so | Rules R9–R11 (+ jar-test hint M4); `limit_note` shown on screen |
| MRL Passport is self-reported | Buyer over-trusts it | Label it "spray record + risk estimate"; lab test stays with exporter | Note on the passport page |
| Dealer backlash | Farmer pressured | Bill Scan output is private to the farmer; no dealer named unless the farmer reports | Bill results are not shared; shop name is optional |
| Data privacy | Location and identity exposure | Hash phone numbers; opt-in location; officers see aggregates | No phone number collected; salted hash of a device id; location only if the phone shares it; dashboards show districts and batches |
| Medical liability (SOS) | Harmful advice | Only label text + NPIC helpline + nearest facility; no own treatment advice | Doctor Card repeats label text; LLM never used on the SOS path; disclaimer shown and spoken |
| Low smartphone literacy | Low adoption | Voice, icons, FPO field staff onboarding; IVR on the roadmap | Voice by default in 5 languages, picture grid, one decision per screen |
| Rules change (new bans, QR rollout) | Stale verdicts | Rules stored as data with effective dates; admin screen to add a ban in minutes | `rules.json`; state bans and national bans with effective dates; `/app/officer/admin` |

**Ethics line for the pitch:** "DawaCheck helps farmers ask the right question at the shop. It does not replace the agriculture officer, the lab or the doctor."
