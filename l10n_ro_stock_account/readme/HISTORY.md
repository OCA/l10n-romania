## 19.0.0.26.1

- Fix silent over-delivery in `stock_move._split_for_fifo_assignment`: it
  walked the per-location FIFO stack for `product_uom_qty`/`product_qty` -
  the *ordered* demand - instead of `quantity`, the amount actually being
  shipped on this transfer. Reducing `quantity` below the ordered demand so
  the remainder backorders is the normal Odoo workflow (core's own
  `_create_backorder` compares `quantity` against `product_uom_qty` for
  exactly this); `product_uom_qty` is supposed to stay at the full order.
  Consuming/valuing FIFO layers against the full order instead of the
  actual shipped quantity meant that whenever satisfying the (wrongly
  inflated) target required more than one price layer, the split created
  an extra `stock.move` for the difference and shipped it too - delivering
  the full original demand regardless of what was actually picked, with no
  backorder. When a single layer happened to cover the full order the bug
  was silent (wrong valuation, same visible outcome). The split now walks
  the stack for `quantity` (what's actually shipping), matching what core
  already uses for its own backorder decision; a consistency check raises
  a clear error instead of silently completing the transfer if the amount
  accounted for by the split still doesn't match.

## 19.0.0.25.1

- Fix `IndexError: list index out of range` in
  `stock_move._l10n_ro_process_fifo_split` when validating an outgoing move.
  An incoming move with nothing left to consume (its valued quantity is zero,
  for instance a reception corrected to 0 after validation) still entered the
  per-location FIFO stack; `_split` returns no values for a quantity that is
  zero at the UoM rounding, so indexing its result crashed the transfer. Such
  moves no longer enter the stack, zero-quantity slices are skipped by the
  outgoing split, and the quantities are compared with the UoM rounding
  instead of raw floats.

## 19.0.0.19.1

- Fix `TypeError: '<' not supported between instances of 'bool' and 'str'` in
  `stock_move._compute_account` when sorting the account move lines. A journal item
  without an account (or whose account has no code) returns `False` for
  `account_id.code`, which cannot be compared against the string codes of the
  other lines. The sort key now falls back to an empty string, and the
  subsequent `code[0]` check guards against an empty/falsy code.
