## 19.0.0.8.1

- Fix a foreign tax ID being silently prefixed with its country code on every
  save, which made it impossible to store the number in its local form. A
  Hungarian 11-digit adószám (`26173247-2-08`) became `HU26173247-2-08` on
  create, and removing the prefix brought it back on the next write. Since VIES
  only recognises the 8-digit EU form (`HU26173247`), the intra-Community check
  kept answering `unassigned`, `vies_valid` stayed unset and the
  intra-Community fiscal position was never selected, so the invoice was taxed
  at the domestic rate instead of being exempt.
- The cause was `_split_vat` deducing the country code from a database lookup
  (`search([("vat", "=", vat)])`): during create/write the record is already
  stored when `_check_vat` runs, so it matched itself and `_run_vat_checks`
  re-attached the prefix. The country code is now taken from the record being
  parsed, and only for a bare numeric CUI, so writing a Romanian CUI without
  the `RO` prefix keeps working.
- Dropping the lookup also removes one `search` per `_split_vat` call - the
  method is used by `_compute_l10n_ro_vat_number` and by several core and
  Enterprise localisations - and the non-deterministic result when the same
  `vat` string existed on partners from different countries (`limit=1` picked
  one arbitrarily).
