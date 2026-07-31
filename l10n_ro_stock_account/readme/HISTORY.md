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
