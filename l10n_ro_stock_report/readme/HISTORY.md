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
