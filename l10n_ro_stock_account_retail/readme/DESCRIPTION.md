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

## Configuration

A retail warehouse is set up by ticking *Retail Warehouse* on
`stock.warehouse` and assigning a *Retail Pricelist*. All internal
locations under that warehouse become retail locations automatically.

The **markup (378)** and **deferred VAT (4428)** accounts are resolved
in this order:

1. `stock.location.l10n_ro_account_markup_id` /
   `l10n_ro_account_deferred_vat_id` (per company)
2. `product.template.l10n_ro_account_markup_id` /
   `l10n_ro_account_deferred_vat_id` (per company)
3. `product.category.l10n_ro_account_markup_id` /
   `l10n_ro_account_deferred_vat_id` (per company)
4. `res.company.l10n_ro_account_markup_id` /
   `l10n_ro_account_deferred_vat_id` (defaults)

## Accounting flow

The retail price (PVA) for a product in a warehouse comes from the
warehouse pricelist, interpreted through the product taxes. Standard
`l10n_ro_stock_account` keeps booking the cost. This module adds the
markup leg automatically when a `stock.move` crosses the retail
boundary:

- **Into a retail location**: `Dr 371 / Cr 378` (markup) and
  `Dr 371 / Cr 4428` (VAT)
- **Out of a retail location**: `Dr 378 / Cr 371` and
  `Dr 4428 / Cr 371`
- **Between two retail warehouses with different pricelists**: both
  legs are booked (reverse at source, create at destination)
- Internal moves staying inside the same retail warehouse generate no
  extra entries.

## Retail price changes — Proces Verbal de Schimbare Pret

`l10n.ro.retail.price.change` is a persistent document
(*Proces Verbal de Schimbare Pret*) numbered by sequence
`PVSP/YYYY/00000`. It captures: warehouse, date, on-hand products,
old vs. new PVA per line, with markup / VAT splits.

There are two flows:

1. **Manual** — create a draft Proces Verbal, load on-hand products,
   edit new prices, then post. On post the warehouse pricelist is
   updated and the delta entries are booked.
2. **Automatic** — when a `product.pricelist.item` on a retail
   pricelist is created or its `fixed_price` is modified, a draft
   Proces Verbal is generated for each affected retail warehouse with
   on-hand stock. The user reviews and posts it to book the
   revaluation.

## Retail stock report

`l10n.ro.stock.retail.report` lists per (warehouse, location,
product): on-hand qty, cost, current PVA (from pricelist + tax),
markup, deferred VAT and retail value (matching 371).
