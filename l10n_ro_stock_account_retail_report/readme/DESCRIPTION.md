# Romania - Retail Stock Report (Marfa in Magazin)

Reporting for the retail merchandise accounting of
`l10n_ro_stock_account_retail`.

## Retail stock

`l10n.ro.stock.retail.report` lists, per (warehouse, product), the
quantity on hand, its cost, the markup (378) and the deferred VAT (4428)
actually carried by that stock, and the retail value they add up to -
which is what account 371 holds.

The figures come from the markup ledger, so they are what is on the
accounts, not a recomputation from the current pricelist. A **To
Revalue** column shows the difference between the current shelf price
and what the stock carries: anything other than zero means a Proces
Verbal de Schimbare Pret is due for that product.

## Storage sheet

Retail columns on the Romanian storage sheet (fisa de magazie) are not
implemented yet; the module already depends on `l10n_ro_stock_report` so
they can be added here without moving anything.
