## 19.0.1.0.0

- On a reception on notice, take the price difference from what is left on the 408 pivot once
  the exchange rate difference is recognised, instead of comparing the invoice value with the
  stock value. The old comparison mistook the rate delta for a price difference and capitalised
  it into inventory, on top of the 765/665 entry booked by `l10n_ro_stock_account` - the same
  delta twice on 408, and inventory retranslated for an exchange rate movement, which IAS 21 and
  OMFP 1802 do not allow for a non-monetary asset. The residual is computed analytically, so it
  is still available before posting for the price difference confirmation dialog and it stays
  correct on partial invoicing.

