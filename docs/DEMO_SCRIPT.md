# Demo script (3 minutes)

**Live site:** https://dawacheck-theta.vercel.app/ · **Dashboard:** https://dawacheck-theta.vercel.app/#/officer

Setup: laptop with two browser tabs, tab 1 the website (home page), tab 2 the officer dashboard. Optional: the same site on a phone, screen-mirrored, to show it works on a farmer's phone. Before going on stage, open both tabs once so they are warm, and check `/api/health` says `postgresql+psycopg`.

| Time | Say | Do on the website |
|---|---|---|
| 0:00–0:20 | "Yavatmal, 2017. Over 20 farmers died and about 800 reached hospital after spraying cotton. Doctors did not know which poison it was. The farmer had bought what the dealer gave him." | Title slide / home page |
| 0:20–0:35 | "Every farming app tells you the disease. Nobody checks the bottle. DawaCheck does: is it registered, approved for this crop, how much, can I mix it, when can I harvest." | Home page: point at the headline and the four tiles |
| 0:35–0:55 | "Ramesh grows cotton in Yavatmal. The dealer gives him Blastguard." | Tap **Blastguard 75** (Try it now) → **yellow**: not approved for cotton, approved options listed. Tap **Why?**: the rule and its source |
| 0:55–1:15 | "His neighbour in Punjab grows basmati for export." | Home → tap **Tricy Plus** → **red**: banned for basmati in Punjab since 2025-06-14 |
| 1:15–1:35 | "Now the right product. How much, and when is the harvest safe?" | Home → tap **Emacure** → **green** → **Next**: dose per tank, measuring cap, safety gear, safe harvest date → **Save spray** |
| 1:35–1:55 | "He brings home this bill." | **Scan bill** → type `Kavach Imida`, `250 ml`, qty `2`, `₹1440`; **+ Add product** `Blastguard 75`, `120 g`, `1`, `₹290` → **Check** → Blastguard yellow, "same chemical available for ₹646 less" |
| 1:55–2:10 | "He plans to mix two products in one tank." | **Mix check** → pick `Chlorokill 20` and `Pyrikill` → R9 same chemical twice (double dose), R11 two toxic products |
| 2:10–2:30 | "Every scan also protects the next farmer." | Home → tap **Profex 50** → **red**: batch reported by other farmers. Switch to tab 2: dashboard map, red cluster in Yavatmal, Suspicious batches table |
| 2:30–2:45 | "If he still feels sick, one button." | **SOS** (top right) → poison helpline 1800 116 117, first aid from the label, **Show Doctor Card** |
| 2:45–3:00 | "AI only reads the label; fixed rules with government sources decide. Free for farmers; exporters, FPOs and state departments pay. Plantix tells you the disease. DawaCheck takes responsibility from the dealer's shop to the dinner plate." | Home page |

**If a judge hands you a real packet:** Scan packet → Take photo (or type the chemical line). If the brand is not in our catalogue, the site still checks the chemical and formulation (crop approval, dose, waiting period, safety) and says "Brand not in our catalogue yet".

**Language:** switch English → हिंदी / मराठी in the header at any point; tap **Listen again** on a verdict.

**Say this if asked about data:** "The rules engine and the CIB&RC import pipeline are built; the site runs on sample data today and says so on every screen. Loading the official Major Uses PDFs is the next step."

**Worked rule examples** (all covered by tests):
1. Wrong crop: `Blastguard 75` (tricyclazole, rice) scanned for cotton → R5 yellow + cotton options.
2. Basmati in Punjab: `Tricy Plus` for basmati, state Punjab → R7 red.
3. Tank mix: `Chlorokill 20` + `Pyrikill` → R9 double dose, R11 toxicity.
4. Early harvest: spray 1 Oct, 14-day waiting period, harvest 10 Oct → R12 "safe from 15 Oct".
5. Real brand not in the catalogue (e.g. imidacloprid 17.8 SL) → checked at formulation level, G1 note.

**Backups:** a screen recording of the full demo; the four "Try it now" buttons work without a camera; the dashboard tab already open.
