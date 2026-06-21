# Changelog

## 18.0.0.2.1

- Fix partner merge failing with the VAT/NRC uniqueness constraint: the
  `partner_merge` context is now propagated both to the source/auto-picked
  partners (via `self`) and to an explicitly passed destination partner, so the
  constraint is correctly skipped during a merge.
