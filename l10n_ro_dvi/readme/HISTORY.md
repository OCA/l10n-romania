## 19.0.0.10.0 (2026-11-23)

- The DVI carries its own accounts for the customs duty, the customs
  commission and the VAT paid at customs. They start from the customs duty
  and commission products and can be changed on each DVI.
- The customs duty and commission products are created with the first 446x
  and 447x account: the search for them never matched before, so the duty
  and the VAT paid at customs landed on the expense account of the product
  category (607).
- A DVI can be created in code or by import: the defaults are ids, not
  records.
