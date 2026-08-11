## 18.0.1.29.0

- Fix the valuation of an internal transfer between two valuation accounts
  (gestiuni). The outgoing leg was valued at `product.standard_price`, i.e. the
  average cost over ALL the valuation accounts of the product, so whenever the
  source account held the goods at a different cost the transfer took out more
  (or less) than that account owned. The source account was left with value and
  no quantity, the accounting entry (which follows the outgoing leg) moved the
  wrong amount, and the discrepancy showed up both in the storage sheet and in
  the trial balance. Both legs are now valued at the cost the source account
  actually holds for the transferred goods, so a transfer neither creates nor
  destroys value. FIFO products are unaffected: they already consume the real
  layers.

## 18.0.1.25.1

- Fix `TypeError: '<' not supported between instances of 'bool' and 'str'` in
  `stock_valuation_layer._compute_account` when sorting the account move lines.
  A journal item without an account (or whose account has no code) returns
  `False` for `account_id.code`, which cannot be compared against the string
  codes of the other lines. The sort key now falls back to an empty string, and
  the subsequent `code[0]` check guards against an empty/falsy code.
