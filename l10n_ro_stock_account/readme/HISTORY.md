## 19.0.1.8.0

- Fix dropship moves retroactively repricing unrelated real stock of the
  same product, for average-cost (AVCO) products. Core `stock_account`'s
  `_set_value()` adds a move's product to `products_to_recompute` whenever
  `is_dropship or is_in` is true, regardless of whether the move ends up
  contributing any value there, and later recomputes the average cost for
  every product in that set. Core's own averaging engine
  (`product._run_average_batch`) explicitly includes `is_dropship` moves in
  the same moving-average pool as real purchases, and since Odoo 19 derives
  average-cost quant values live from `standard_price`, that recompute
  retroactively changes the reported value of a product's real stock held
  elsewhere, purely because the same product was also dropshipped — even
  though the dropship transaction never touched that stock. Confirmed this
  reproduces in plain Odoo (no Romanian accounting involved) as well as on
  a Romanian-accounted company before this fix. Dropship moves now bypass
  core's `_set_value()` entirely on Romanian-accounted companies (this
  module already sets their `value` itself, see the 19.0.1.7.0 entry
  below) so they never enter that recompute. FIFO products were never
  affected: core's FIFO branch reprices existing stock strictly from its
  own `total_value`/`qty_available`, neither of which a dropship move ever
  touches.

## 19.0.1.7.0

- Fix missing stock valuation entries for dropshipped stock moves. A move
  from a supplier location straight to a customer location (dropship) never
  gets `stock.move.value` populated by core `stock_account`: `_action_done`
  routes it through the same `moves_in._set_value()` call used for regular
  incoming moves (the filter is `is_in or is_dropship`), but the assignment
  `move.value = move._get_value()` inside `_set_value` only runs when
  `is_in` is true, never for a pure dropship move. On top of that,
  `_get_l10n_ro_move_type_account_list()` mapped `"dropshipped"` and
  `"dropshipped_return"` to an empty account list, so even a correctly
  valued move would have produced no accounting line. Combined, the vendor
  bill kept debiting the stock valuation account (371) on receipt, the
  customer invoice kept crediting the sale account (707) as usual, but the
  stock side was never credited back and the cost of goods sold expense
  account (607) was never debited — the stock valuation account accumulated
  an ever-growing balance with no goods behind it, and gross margin was
  permanently overstated by the un-recognised cost. Dropship moves now get
  `value` populated the same way `internal_transfer` moves already do in
  this module, and use the same account mapping as `delivery`/
  `delivery_return` (debit expense, credit stock valuation, symmetric on
  the return). This only affects new moves going forward; historical
  dropship moves already validated before this fix keep their original
  (missing) accounting and need a separate, deliberate regularisation
  entry if the accumulated balance is to be cleared.

## 19.0.1.5.0

- Keep the standard valuation for an internal transfer whose source warehouse
  holds a negative balance with goods still on hand, a state left behind by
  earlier mis-valuations. The per-warehouse cost is the balance over the
  quantity, so such a warehouse yields a negative cost; valuing the move at it
  made the move value negative, which ran the whole entry backwards: the
  source warehouse came out debited instead of credited, so the transfer
  deepened its negative balance instead of relieving it.

## 19.0.1.3.0

- Value an internal transfer at the cost the source warehouse actually holds
  for the product, instead of the product's global average. Both legs of the
  transfer entry are built from a single `stock.move.value`, so they can never
  diverge on this series - what was wrong is the amount itself: a transfer
  between two warehouses took out of the source warehouse the average computed
  over *all* warehouses. When that average was higher than what the source
  warehouse held, the warehouse was left with value and no quantity to carry
  it (and the other way round when it was lower), which is what the storage
  sheet shows per warehouse. The accounting stayed balanced throughout, only
  the per-warehouse valuation was off.
- The new `_l10n_ro_get_source_account_unit_cost` rebuilds that cost from the
  done moves in and out of the locations sharing the source valuation account.
  It is plugged into `_get_value_from_std_price`, the last step of the standard
  valuation chain, so a value coming from a bill, a quotation, a return or a
  landed cost keeps priority exactly as before; only the fallback to the
  product's global cost is replaced. FIFO and lot valued products are left
  alone - there the cost already comes from the layers or from the lot - and so
  are source locations without a valuation account of their own, where there is
  no per-warehouse cost to follow.
- Same defect as the one fixed on 18.0 by `_l10n_ro_get_source_account_unit_cost`
  in 18.0.1.29.0, but with a different mechanism: on this series the valuation
  layer is gone and the value lives on the move.

## 19.0.1.1.1

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

## 19.0.1.0.0

- Recognise the exchange rate difference on the 408 pivot (*Furnizori - facturi nesosite*) when
  a reception on notice (`picking.l10n_ro_notice`) comes from a purchase order in a foreign
  currency. Until now the 408 leg of the notice entry was booked in company currency only, so
  the order currency was lost and nothing could compute the rate delta: it stayed as a silent
  balance on 408, a manual reconciliation could not clear it, and the stock ledger drifted away
  from the stock account by that same delta.
- The 408 leg now keeps the order currency, since the estimated liability is a monetary item,
  while the stock leg stays in company currency at the reception rate. When the invoice is
  posted, the rate delta on the quantity already received is booked as `Dr 408 / Cr 765`
  (favourable) or `Cr 408 / Dr 665` (unfavourable) - per OMFP 1802/2014 the function of account
  408 lists exactly these differences as "recorded when the invoice is received". The lines are
  `cogs` lines on the bill, so the invoice total is untouched, they stay out of the e-invoice
  and they are removed when the bill is reset to draft.
- Account 408 therefore does **not** need to be reconcilable: the pivot closes by document, not
  by matching amounts. No reconciliation is attempted.
- `_get_value_from_bill` keeps the reception rate for the quantity received on notice, so
  inventory is no longer revalued for exchange rate movements (IAS 21 / OMFP 1802: a
  non-monetary asset is not retranslated) and the stock ledger agrees with the stock account.
  Only the quantity invoiced beyond the reception - a genuine price difference, whose liability
  arises at the invoice date - is taken at the invoice rate.

## 19.0.0.26.1

- Expose the `stock.move.l10n_ro_move_type` selection as the module level
  `MOVE_TYPE` constant, so other modules can reuse it instead of duplicating the
  list. Up to 18.0 the same list was available as `VALUED_TYPE` on
  `stock.valuation.layer`. No functional change.

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
