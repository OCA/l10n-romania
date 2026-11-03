## 19.0.2.12.0

- Read the moves line by line: each line keeps its own locations and its
  quantity in the product unit, and takes the share of the move value matching
  that quantity. A move recorded on a parent location whose lines stored the
  goods in sublocations left one location negative and another positive on the
  detailed sheet. Moves without quantity on their lines (value-only moves) keep
  their locations and value with a zero quantity, since stock only changes
  through move lines. This replaces the unit conversion on the move quantity
  of 19.0.2.10.0: the line quantity is already in the product unit.
- Include archived internal locations when no location is selected, and read
  the report locations with ``active_test=False``: goods received in a location
  archived later dropped out of the opening balance.
- Group the values on the valuation account the product has today (location,
  product, then category account), not on the account stored on the move:
  after a category change the stock entered on the old account and left from
  the new one, leaving the old account positive and the new one negative, while
  the balance sheet carries it all on the new account.

## 19.0.2.9.0

- Fix the "Toate locațiile" (all-locations) storage sheet report: the printed
  FINAL row recomputed a running total from the individual in/out detail
  lines instead of using the already-correct `quantity_final`/`amount_final`
  stored on the FINAL line. The `t-if` meant to branch on the FINAL row
  (`product!=line_product.product_id`) is always false, since the lines it
  iterates are already filtered to a single product, so every row, FINAL
  included, went through the running-sum branch instead. Ported from the
  18.0 fix, where a manual correction layer with no valued type was silently
  dropped from the in/out detail queries and so was missing from the running
  total while still counted in the correctly-computed final sum. The
  in/out queries were rewritten for 19.0 (stock.valuation.layer removed) and
  no longer have that specific exclusion, but the template still recomputes
  instead of trusting the stored final value, which stays fragile to any
  future gap between the detail and final queries. The single-product report
  (`report_storage_sheet`) was not affected, it already reads the final line
  separately.

## 19.0.2.6.0

- Give the opening and closing balance rows a valued type of their own,
  `initial` and `final`. This changes the behaviour deliberately kept in
  19.0.2.4.1 ("balance rows keep no valued type, as in 18.0, since a balance
  aggregates several move types"), and the reasoning behind it is worth
  restating: a balance does aggregate several move types, which is exactly why
  it should not share a group with the movements whose type could not be
  determined. Left untyped, both balances fall into the same empty-type bucket
  as those movements, and grouping by valued type then produces a row showing an
  opening balance differing from the closing balance with no movement in
  between - the movements being on the typed rows. Every figure in that row is
  correct, but accountants read it as a broken sheet and open tickets against
  it. Typing the balances keeps them legible as balances and leaves the
  empty-type bucket to mean only what it says.

## 19.0.2.4.1

- Fix the storage sheet no longer splitting by valued type. Up to 18.0 the
  valued type of a line came from the valuation layer
  (`svl.l10n_ro_valued_type`); Odoo 19 removed `stock.valuation.layer` and moved
  the valuation onto `stock.move`, so the report hardcoded `'indefinite'` on
  every movement row and grouping by "Valued Type" collapsed into a single
  group. The in/out queries now read the stored
  `stock_move.l10n_ro_move_type` column and group by it, and the line's
  selection lists every move type again so the values are groupable and
  readable. Balance rows keep no valued type, as in 18.0, since a balance
  aggregates several move types.
