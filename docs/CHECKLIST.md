# Final checklist (playbook section 19) with status

✅ done in this repository · ⏳ needs people, real data or the venue

## Before the hackathon
- ⏳ Hackathon format, deadlines, slide limit and judging rubric confirmed
- ⏳ Competitor search repeated (GitHub, Devfolio, Play Store, Product Hunt) and results noted
- ⏳ Every number on the slides re-opened at its source and the year written next to it (list in `DATA_SOURCES.md`)
- ⏳ Major Uses parsed for rice, cotton, tomato: ✅ parser built and tested; ⏳ run it on the real PDFs (site blocked from the build environment)
- ✅ 30-question test set and harness (`data/kb_questions.json`); ⏳ rewrite answers from the real PDF pages
- ⏳ 50 real packs photographed and in the catalogue (demo catalogue is fictional)
- ⏳ OCR + extraction accuracy measured on those 50 packs
- ⏳ Wireframes tested with 3 outsiders
- ⏳ Demo products chosen and each verdict checked against the PDF page

## During the build
- ✅ Core loop: scan → confirm → verdict → dose → save
- ✅ Bill Scan, Cocktail Checker, Doctor Card, MRL Passport
- ✅ Radar map showing a red cluster from scans (seeded + live)
- ✅ Voice in 4 languages (drafts; ⏳ native-speaker review)
- ✅ Offline mode for products already scanned (cached verdicts + app shell)
- ⏳ Feature freeze at hour 32

## Before the pitch
- ✅ Pitch deck: `docs/DawaCheck_pitch.pptx` (regenerate with `docs/deck/build_deck.js`); ⏳ add team name, demo-video QR and measured accuracy
- ⏳ Backup demo video recorded and linked by QR on the last slide
- ⏳ Second phone ready; printed labels in the bag
- ⏳ Pitch rehearsed 3 times within the time limit
- ✅ Judge answers written (`JUDGE_QA.md`); ⏳ every member can answer them
- ✅ Limitations stated (README "Honest limits", slide 10 ethics line)
