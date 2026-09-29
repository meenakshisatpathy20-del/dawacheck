# Final checklist (playbook section 19) with status

✅ done in this repository · ⏳ needs people, real data, network access or the venue

## Before the hackathon
- ⏳ Hackathon format, deadlines, slide limit and judging rubric confirmed
- ⏳ Competitor search repeated (GitHub, Devfolio, Play Store, Product Hunt) and results noted
- ⏳ Every number on the slides re-opened at its source and the year written next to it (exact links in `DATA_SOURCES.md`)
- ✅ Major Uses, registered-products and banned-list parsers built and tested · ⏳ run them on the real PDFs (`python -m pipeline.run --download --load`; ppqs.gov.in was blocked from the build environment)
- ✅ 30-question test set and harness · ⏳ rewrite answers from the real PDF pages
- ✅ Catalogue of 50 products (fictional) · ⏳ 50 real packs photographed and loaded
- ✅ Accuracy harness (`scripts/accuracy_report.py`) · ⏳ OCR + extraction accuracy measured on the 50 real packs and 5 real bills
- ⏳ Wireframes tested with 3 outsiders
- ⏳ Demo products chosen and each verdict checked against the PDF page

## During the build
- ✅ Core loop: scan → confirm → verdict → dose → save
- ✅ Bill Scan, Cocktail Checker, Doctor Card, MRL Passport
- ✅ Radar map showing a red cluster from scans (seeded + live), with heat layer
- ✅ Voice in 5 languages (drafts) · ⏳ native-speaker review; ⏳ record clips with `scripts/make_voice_clips.py`
- ✅ Offline mode for products already scanned
- ⏳ Feature freeze at hour 32

## Before the pitch
- ✅ Pitch deck `docs/DawaCheck_pitch.pptx` with real app screenshots (regenerate with `docs/deck/build_deck.js`) · ⏳ add team name, demo-video QR, measured accuracy, real crop photos
- ⏳ Backup demo video recorded and linked by QR on the last slide
- ⏳ Second phone ready; printed labels in the bag
- ⏳ Pitch rehearsed 3 times within the time limit
- ✅ Judge answers written (`JUDGE_QA.md`) · ⏳ every member can answer them
- ✅ Limitations stated (`RISKS.md`, README "Honest limits", slide 10 ethics line)
