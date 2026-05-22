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
