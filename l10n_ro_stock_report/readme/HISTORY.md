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
