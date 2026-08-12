## 18.0.1.6.0

- Apply the internal transfer fix from `l10n_ro_stock_account` 18.0.1.29.0 here
  as well. This module fully overrides `_create_internal_transfer_svl`, for
  every cost method and not only for FIFO, so a non FIFO product was still
  valued at `product.standard_price` — the average cost over ALL the valuation
  accounts of the product — whenever this module was installed. Both legs are
  now valued at the cost the source valuation account actually holds for the
  transferred goods. FIFO keeps consuming the real layers, unchanged.
