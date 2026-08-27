## 18.0.1.10.0

- Fix the "Toate locațiile" (all-locations) storage sheet report: the printed
  FINAL row recomputed a running total from the individual in/out detail
  lines instead of using the already-correct `quantity_final`/`amount_final`
  stored on the FINAL line. A stock valuation layer with no
  `l10n_ro_valued_type` set (e.g. a manual correction) is silently excluded
  from the in/out detail queries (`l10n_ro_valued_type != 'reception_return'`
  evaluates to `NULL`, not `TRUE`, for a `NULL` value), so any such layer was
  missing from the running total while still counted in the correct final
  sum — the on-screen pivot view (which reads the stored field directly)
  matched the balance, the printed/PDF report did not. The single-product
  report (`report_storage_sheet`) was not affected, it already reads the
  final line separately.
