# Demo script (3 minutes)

One speaker, one person on the phone (screen-mirrored), one on the dashboard laptop (`/app/officer`). Every scan uses a pack you have tested. Before going on stage: `python -m app.seed --reset`, set the farmer's crop to **cotton**, state **maharashtra**, language **मराठी**. Show the Impact tab on the dashboard at the end if asked about business.

| Time | Say | Do in the app (demo data) |
|---|---|---|
| 0:00–0:20 | "Yavatmal, 2017. Over 20 farmers died and about 800 reached hospital after spraying cotton. Doctors did not know which poison it was. The farmer had bought what the dealer gave him." | Slide 2 |
| 0:20–0:35 | "Every farming app tells you the disease. Nobody checks the bottle. DawaCheck does." | Home screen |
| 0:35–1:05 | "Ramesh brings home this bill." Scan the bill. "One product is not approved for cotton, and the same chemical costs less." | Scan bill → items `Kavach Imida` 250 ml ×2 ₹1440 and `Blastguard 75` 120 g ₹290 (crop cotton, pest jassid) → Blastguard is yellow (R5); cheaper imidacloprid shown |
| 1:05–1:30 | "He plans to mix these two." Scan both. "Same chemical twice: double dose." | Mix check → Scan packet for each (or pick) `Chlorokill 20` + `Pyrikill` → R9 double dose, R11 toxic mix, spoken in Marathi |
| 1:30–1:50 | Scan the approved alternative. "This much per tank, this many tanks, wear gloves, rain at 4 pm so spray tomorrow." | Scan `Emacure` (QR `DC-QR-1012\|EM25-777\|0001`) → Yes on the confirm screen → green → Next → dose card with measuring cap, gear icons, weather line (use `DAWACHECK_OFFLINE=1` + `/weather-window?demo=rain` if Wi-Fi fails) → Save spray (reminder set) |
| 1:50–2:10 | "If he still feels sick, one button." Press SOS. | SOS → Show Doctor Card (filled from the saved spray) + 1800 116 117 |
| 2:10–2:30 | "Gurpreet grows basmati for export." Show the spray diary. "Safe to harvest from this date; no chemical on Punjab's banned list." | Switch crop to basmati, state punjab; log `Pymet 50` for brown plant hopper → My sprays → passport QR, open on a second phone |
| 2:30–2:50 | "Every scan also protects the next farmer." Scan a pack whose batch was seeded with a conflicting date. | Scan packet → type the QR code `DC-QR-1007\|PF24-117\|0001` (Profex 50, batch PF24-117) → Yes → red R8 "Other farmers reported this batch"; dashboard map shows the Yavatmal cluster |
| 2:50–3:00 | "Plantix tells you the disease. DawaCheck takes responsibility for the dose, from the dealer's shop to the dinner plate." | Closing slide |

**Worked rule examples** (all covered by tests):
1. Wrong crop: `Blastguard 75` (tricyclazole, rice) scanned for cotton → R5 yellow + cotton options.
2. Basmati in Punjab: `Tricy Plus` for basmati, state Punjab → R7 red "banned for basmati in Punjab since 2025-06-14".
3. Tank mix: `Chlorokill 20` + `Pyrikill` → R9 double dose.
4. Early harvest: spray 1 Oct, 14-day waiting period, harvest 10 Oct → R12 "safe from 15 Oct".

Before the real demo, replace the sample products with packs you photographed and check each verdict against its PDF page.

**Backups:** recorded video of the full demo; printed pack labels; `DAWACHECK_OFFLINE=1`; a second phone with the app installed (Add to Home Screen) and the products already scanned once, so cached verdicts work in airplane mode.
