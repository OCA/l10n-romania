# Romania - Stock Accounting Retail (Marfa in Magazin)

Implements the Romanian retail merchandise accounting (gestiunea
mărfurilor la preț de vânzare cu amănuntul), as described in the
standard monograph for retail commerce:

- **371 Mărfuri** — stock valued at retail price with VAT
- **378 Diferențe de preț la mărfuri** — markup (adaosul comercial)
- **4428 TVA neexigibilă** — VAT included in the retail price, not yet
  collected
- **607 Cheltuieli privind mărfurile** — cost of goods sold
- **707 Venituri din vânzarea mărfurilor** — retail revenue (booked
  from the POS / sales invoice, not by this module)

This is the kernel of the family: it defines what a retail location is,
where the shelf price comes from, and how the markup is booked. The
price change document, the reporting and the point of sale treatment
live in modules of their own:

- `l10n_ro_stock_account_retail_price_change` — the price change
  document, its report and the price history on the product
- `l10n_ro_stock_account_retail_report` — retail stock reporting
- `l10n_ro_stock_account_retail_landed_cost` — keeps 371 at the shelf
  price when a landed cost raises the cost
- `l10n_ro_stock_account_retail_price_difference` — shows what a vendor
  bill leaves of the markup, before it is posted
- `l10n_ro_stock_account_retail_picking_report` — cost, markup and shelf
  price columns on the goods receipt note
- `l10n_ro_stock_account_retail_pos` — keeps the point of sale closing
  entry from discharging the stock a second time

## Configuration

A retail warehouse is set up by ticking *Retail Warehouse* on
`stock.warehouse` and assigning a *Retail Pricelist*. All internal
locations under that warehouse become retail locations automatically.

The **markup (378)** and **deferred VAT (4428)** accounts are resolved
in this order:

1. `stock.location.l10n_ro_account_markup_id` /
   `l10n_ro_account_deferred_vat_id`, walking up the parent locations,
   so a shop is configured once and its shelves and bins inherit it
2. `product.template.l10n_ro_account_markup_id` /
   `l10n_ro_account_deferred_vat_id` (per company)
3. `product.category.l10n_ro_account_markup_id` /
   `l10n_ro_account_deferred_vat_id` (per company)
4. `res.company.l10n_ro_account_markup_id` /
   `l10n_ro_account_deferred_vat_id` (defaults)

## The retail price is held VAT included

A price on a retail pricelist is the PVA: the figure on the shelf
label, what the customer pays, and what account 371 carries. The
product taxes are used to split it into the base the markup is measured
against and the deferred VAT inside it — never to add VAT on top.

Those taxes are the product's sale taxes **mapped through the fiscal
position of the shop** (`l10n_ro_fiscal_position_id` on the warehouse,
the one Romanian stock accounting already uses to map valuation
accounts). A company selling both retail and B2B keeps one set of taxes
on the product and maps them per shop — to the VAT included variants a
till works with, or to another rate — and the VAT loaded on 4428 has to
be the one that shop will actually collect. The same fiscal position
maps the three accounts an entry touches, so a shop keeping its goods
on a 371 of its own says it once instead of overriding every product,
category and location.

A mapping to the *price included* variants of the same taxes changes
nothing: the shelf price is read as VAT inclusive whatever the tax says
about itself, so only a change of rate moves the split.

Only the VAT part of those taxes reaches 4428. A charge collected for
somebody else — a packaging deposit (SGR), an eco fee — is kept out of
the split and out of the value carried on 371; nothing on a tax says
whether it is VAT, so mark those with *Not VAT (Retail)* on the tax
(on every variant a fiscal position can map to). Sale taxes are treated
as VAT unless it is ticked.

The shelf price has to come from a rule on the retail pricelist of the
warehouse. There is no fallback on the product sale price: that is a
price *without* VAT in a standard Romanian setup, so booking it as a
PVA would put the wrong figure on 371, understate the markup and
compute the deferred VAT on a different base — silently. A product
without a price on the shop's retail pricelist is refused instead.

## Accounting flow

Standard `l10n_ro_stock_account` keeps booking the cost. This module
adds the markup leg when a `stock.move` crosses the retail boundary:

- **Into a retail location**: `Dr 371 / Cr 378` (markup) and
  `Dr 371 / Cr 4428` (VAT)
- **Out of a retail location**: `Dr 378 / Cr 371` and
  `Dr 4428 / Cr 371`
- **Between two retail warehouses**: both legs are booked, the source
  releasing its own markup and the destination loading its own. A
  multi-step transfer reaches the same result on its own, the transit
  location not being a retail one.
- Moves that stay inside one retail warehouse book nothing.

A shelf price below cost is refused, since it books a negative markup;
a shop that legitimately sells below cost ticks *Allow Selling Below
Cost* on the warehouse.

## The markup ledger

Odoo 19 has no `stock.valuation.layer`: a move carries its cost on
`stock.move.value` and nothing else. The markup and deferred VAT that
sit between cost and shelf price therefore have nowhere to live, and
recomputing them from the current pricelist when the goods leave is
wrong as soon as the price has moved in between — the release does not
match what was loaded, and the difference stays on 378 and 4428 for
good.

`l10n.ro.retail.markup.line` is the subsidiary ledger that holds them.
Every event that changes what 371 carries writes a row: a move crossing
the boundary, a posted price change, later a landed cost or a purchase
price difference. A release is always taken from the balance carried,
prorated over the quantity that carries it — the *coeficient de
repartizare a adaosului comercial* applied per movement — so the last
unit out closes both accounts to zero.

Returns are settled against the move they return, not against today's
price, so a sale return puts back exactly what the sale released.

The ledger is visible under *Inventory → Reporting → Retail Markup
Ledger*, and `stock.quant` publishes the share carried by each quant
next to its cost.

## Demo

`demo/setup_demo.py` builds a complete Romanian retail shop and walks it
through every case the family handles - transfers, sales, returns,
sublocations, a clearance shop, price changes, landed costs, a purchase
price difference, a point of sale session, and both printable documents.
Run it with `odoo-bin shell -d <database> < demo/setup_demo.py`. Each
section is guarded by the module it exercises, so it runs with the kernel
alone and covers more as more of the family is installed.
