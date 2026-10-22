This module provides Romanian-specific stock accounting features that align with Romanian accounting standards and regulations. Below are the configuration options available.

## Overview

The module extends Odoo's standard stock accounting to meet Romanian accounting requirements, providing:

- Location-specific accounting configurations
- Romanian-specific stock valuation accounts
- Product category stock account customization
- Warehouse fiscal position management
- Specialized accounts for stock operations
- Per-location FIFO valuation (vs. Odoo's default company-wide FIFO)
- Automatic negative stock compensation for FIFO products
- Stock valuation entries for dropship deliveries, symmetric with regular deliveries

## Per-location FIFO

For products with `cost_method=fifo`, the module values outgoing moves
against the FIFO stack of the **source location** rather than the
company-wide stack. Each outgoing move is automatically split into one
`stock.move` per FIFO layer (e.g. an outgoing of 4 units from a location
with `IN 2@10` + `IN 3@8` produces a `2x10` move + a `2x8` move).

Internal transfers (`internal → internal` or via transit) are treated as
both `is_in` and `is_out` on the same move:

- they consume from the FIFO stack of the source location,
- they enter the FIFO stack of the destination location with the value
  pulled from the source,
- they generate an accounting entry through the location's valuation
  account (or the company-level transfer account if locations share an
  account).

Controlled by `res.company.fifo_per_location` (defaults to `True` for
Romanian companies, computed from `country_id`, editable per company).

## Negative stock compensation

When a FIFO outgoing move happens before the corresponding incoming move
(i.e. the location FIFO stack is empty), the outgoing value falls back to
the product's `standard_price`. The pending quantity is tracked on the
outgoing move via `fifo_neg_pending_qty` / `fifo_neg_origin_value`.

When the next matching incoming move is posted, the module:

1. allocates the new incoming value across pending outgoing moves (FIFO);
2. updates `stock.move.value` on the outgoing moves to reflect the real
   purchase price;
3. emits an `account.move` correction that debits the variation/COGS
   account and credits the stock valuation account for the delta;
4. links that correction back to the originating IN move via
   `account.move.fifo_neg_origin_move_id` for traceability.

Compensation is idempotent — if `_set_value` is re-invoked on the same IN
move (e.g. when the supplier invoice is posted), the existing
compensation is detected and not duplicated.

Controlled by `res.company.fifo_location_negative_compensation`
(defaults to `True` for Romanian companies, editable per company).

## Dropship valuation

A dropship move (supplier location straight to a customer location, goods
never entering the company's own stock) is now valued and accounted for the
same way a regular delivery is: the vendor bill still debits the stock
valuation account on receipt, and the module now credits that same account
and debits the expense account when the goods leave to the customer,
leaving no residual balance. Without this, the stock valuation account
accumulated a balance that no longer corresponded to any goods on hand, and
the cost of the dropshipped goods was never recognised as an expense.

This applies to dropship moves validated after the fix is installed;
historical dropship moves keep their original (missing) accounting entries
and require a separate, deliberate regularisation if that balance needs to
be cleared.

## Dropship accounting entries

The company never physically holds the dropshipped goods (the supplier
ships straight to the customer), but under Romanian accounting rules stock
is recognised at the transfer of risks and rewards (OMFP 1802/2014, pt. 283
para. 1), not at physical possession — the same principle behind accounts
327 "Goods in transit" and 357 "Goods held by third parties" for stock the
company owns without holding. Routing a dropship purchase through the
stock valuation account rather than expensing it directly at the vendor
bill also keeps a purchase-invoice/sale-invoice timing mismatch (e.g.
vendor bill in December, customer invoice in January) from misstating the
period result, per the accrual principle (pt. 53).

Forward move (goods leave to the customer):

| Account | Debit | Credit |
|---|---|---|
| Expense (607) | value | |
| Stock valuation (371) | | value |

Return move (`dropshipped_return`), storno convention — same accounts as
the forward move, amount in red, not a debit/credit swap:

| Account | Debit | Credit |
|---|---|---|
| Expense (607) | −value | |
| Stock valuation (371) | | −value |

408 "Suppliers - invoices not received" never applies to a dropship move:
that account is a pivot for goods physically received into a warehouse
before the vendor bill arrives, and a dropship move never has that
physical-receipt leg. If the vendor bill is missing at the time of the
customer sale, the correct counterpart is 327 (a stock-in-transit
account), not 408.

For the entry above to stay correct in practice: the credit to 371 must
happen in the same accounting period as the debit from the vendor bill and
for the same amount, so the account nets to zero for dropship traffic at
period end; and dropship quantities should flow through a distinct
location so they never mix into a real warehouse's physical inventory
count.

Dropshipping a product does not affect the value of that same product's
real stock held elsewhere, on either costing method (FIFO or average
cost). Core Odoo's own average-cost engine folds dropship moves into the
same moving-average pool as real purchases by design, which would
otherwise retroactively reprice unrelated stock on hand purely because the
same product was also dropshipped; this module routes dropship moves
around that recompute entirely for Romanian-accounted companies.

## Performance notes

- Partial composite index on `stock_move(product_id, location_dest_id,
  date DESC, id DESC) WHERE state='done' AND is_in=true` powers the FIFO
  stack lookup with index-only scans on large histories.
- Partial index on `stock_move(...) WHERE fifo_neg_pending_qty > 0`
  keeps the compensation search constant-time even with millions of
  historical moves.
- A request-scoped cache (`context['fifo_stack_cache']`) reuses the same
  `_run_fifo_get_stack` result across batched lookups in
  `product._compute_value` and `stock.quant._compute_value` — large
  Inventory Valuation reports drop from O(N) queries to O(distinct
  (product, location)) queries.
