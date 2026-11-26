## 19.0.1.2.0 (2026-11-07)

- Goods entering a shop now print the base goods receipt note (NIR) columns and, appended on the right, the retail columns markup (percent and value), retail price excluding VAT, deferred VAT and retail sale value, in one coherent table. This reverses the earlier behaviour that hid the base valued columns on a retail reception. A transfer into a shop - a purchase received straight into the store or an internal transfer from the warehouse - is treated as a NIR so the retail columns have the reception table to attach to.

## 19.0.1.1.0 (2026-11-07)

- On a retail reception the plain valued money columns (unit price, additional charges, subtotal, taxes, total) are now hidden, so only the retail columns (purchase price and value, markup, shelf price with and without VAT, deferred VAT) print. The table no longer grows to a dozen-odd columns half of which are zero.
- The retail aggregation now skips packed lines when the slip asks for the unpackaged section, so a packed line is no longer charged onto the unpackaged row that shares its key.
