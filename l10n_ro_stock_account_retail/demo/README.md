# Demo for the retail family

`setup_demo.py` builds a complete, runnable Romanian retail shop and walks it through
every case the family handles. Run it with `odoo shell`:

```
odoo-bin shell -d <database> < demo/setup_demo.py
```

Every section is guarded by the module it exercises, so the script runs with the kernel
alone and covers more as you install more of the family.

## What it builds

- a Romanian company with the RO chart of accounts and a stock journal
- 371, 378 and 4428 accounts, with a separate 378/4428 pair per shop set at location
  level, so the priority `location -> product -> category -> company` is exercised
- a FIFO product category and ~30 products with a cost and a shelf price per shop
- three retail shops: MAG1 Bucuresti, MAG2 Cluj, and MAG3 Outlet, which is allowed to
  sell below cost

## Cases it walks through

| Case                                        | What it shows                                                          |
| ------------------------------------------- | ---------------------------------------------------------------------- |
| Purchase orders + receptions + vendor bills | goods enter the depot at cost                                          |
| Depot to shop transfers                     | the markup and deferred VAT are loaded                                 |
| Sales from each shop                        | they are released at what was loaded                                   |
| Shop to shop transfer                       | source releases at its price, destination loads at its own             |
| Shop to depot transfer                      | the markup comes off, back to cost                                     |
| Customer return into a shop                 | settled against the sale, not today's price                            |
| Return out of a shop                        | settled against the reception                                          |
| Transfer into a sublocation                 | the accounts resolve by walking up the parents                         |
| Clearance shop                              | a shelf price under cost, allowed by the warehouse flag                |
| Pricelist change                            | an automatic price change document, then posted                        |
| Manual price change                         | loaded from stock on hand and posted                                   |
| Landed cost that fits                       | 371 unchanged, the markup drops                                        |
| Landed cost that does not fit               | refused, naming the price rise needed                                  |
| Vendor bill above the reception             | the difference lands on the markup                                     |
| Point of sale session                       | opened, sold, closed - and the closing entry carries no stock accounts |
| Both printable documents                    | rendered, to prove the QWeb inheritance still matches                  |

## What it prints at the end

Balances of 371, 378 and 4428; the retail stock report; the products whose shelf price
no longer matches what the stock carries, which is the list a price change document has
to settle; the price change documents raised; and a purchase/sale summary.

Historical snapshots of the retail report are not available. The report is built on the
markup ledger and on the quantities on hand: the ledger carries its own dates, the
quants do not.
