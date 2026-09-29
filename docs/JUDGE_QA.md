# Judge Q&A (answer each in under 20 seconds)

| Question | Answer |
|---|---|
| How is this different from Plantix or FarmerChat? | They identify the disease. We verify the physical product the farmer bought and follow it to harvest. We would happily take their diagnosis as our input. |
| Can your app tell a fake bottle? | It flags red signals: not in the registry, expired, banned, wrong crop, and batches other farmers reported. Only a lab can prove a product is spurious; we route those cases to the agriculture department. |
| What if the AI reads the label wrong? | The AI only reads; the farmer confirms the product; rules decide; every verdict cites the source page. Extraction must pass a JSON schema and regex cross-checks. (Add your measured accuracy on 50 real packs here.) |
| Where does your data come from? | CIB&RC Major Uses and registered-product lists, banned lists, state orders, IRAC/FRAC groups. All public. We turn the PDFs into a queryable database with the file and page on every row. |
| Won't dealers resist? | Honest dealers get a Verified Dealer badge; the Bill Scan helps farmers compare, it does not accuse anyone. |
| How do you reach farmers? | Through FPOs and state agriculture departments first; voice in regional languages; IVR later for feature phones. |
| Who pays? | Exporters and FPOs for MRL Passport, agrochemical brands for counterfeit intelligence, state departments for the enforcement dashboard. Farmers never pay. |
| Is the tank-mix check scientific? | It checks three things we can prove: duplicate active ingredients, same IRAC/FRAC group, stacked toxicity. We do not claim to predict chemical reactions. |
| What about the QR codes the government is mandating? | We read them today and will verify against a central registry if one is published. Until QR is everywhere, OCR covers old stock. |
| Privacy? | No phone numbers are collected; a salted hash of a device id is stored; location only with consent; officers see aggregates and batches, not farmer identities. |

**Say before they ask:** label-claim data in the prototype is sample data until the CIB&RC PDFs are parsed; brand names are placeholders.

Ethics line: *"DawaCheck helps farmers ask the right question at the shop. It does not replace the agriculture officer, the lab or the doctor."*
