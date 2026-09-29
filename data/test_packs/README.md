# Test packs for the accuracy report

Put the 50 real pack photos here (playbook sections 8 and 10), each with a ground-truth file:

```
data/test_packs/kavach-01.jpg
data/test_packs/kavach-01.json   {"brand": "...", "active_ingredient": "imidacloprid", "strength_pct": 17.8,
                                  "formulation": "SL", "batch": "KI25-042", "exp_date": "2027-05",
                                  "reg_no": "CIR-...", "product_brand": "<brand as in the catalogue>"}
```

Real bills go in `data/test_bills/` the same way: `bill-01.jpg` + `bill-01.json` = `{"items": [{"product_name": "...", "price": 1440}]}`.

Then run `python scripts/accuracy_report.py`, which writes `docs/ACCURACY_REPORT.md` (targets: 90% of key fields exact, top-1 product 90%). Put those numbers on the Proof slide.

`scripts/make_synthetic_packs.py` renders clean fake labels to check that the harness works. Those numbers are not evidence of real-world accuracy.
