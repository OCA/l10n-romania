Glue module between `l10n_ro_stock_account` and `sale_mrp` / `mrp_account`.

When a FIFO stock gets empty, Odoo sets the cost of the product to the price
unit of the last incoming move. For a component move linked to the sale line
of a kit (e.g. a customer return of a kit), `sale_mrp` returns the price of one
kit unit instead, so the cost of the component became the price of a whole kit
(e.g. 12 x 6.23 = 74.76 for a pack of 12).

This module keeps the unit value of the incoming move as the cost of the
component. The price of the kit is still used everywhere else (COGS of the kit
on the invoice).
