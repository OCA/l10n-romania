# Demo script for `l10n_ro_stock_account_retail`

`setup_demo.py` builds a runnable, end-to-end demo:
- Romanian chart of accounts on the main company
- One default 378 + 4428 account on the company plus a *location-level*
  override 378.001/4428.001 for MAG1 and 378.002/4428.002 for MAG2,
  exercising the priority `location > product > category > company`
- FIFO product category
- Two retail warehouses (`MG1` Bucuresti, `MG2` Cluj), each with its
  own retail pricelist
- ~30 procedurally-generated products (cost 2–30 RON, MAG1 markup 50 %,
  MAG2 markup 40 %)
- 3 purchase orders (different dates) → reception in the main
  warehouse → vendor bills
- 2 internal transfers (main → MAG1 on 2026-04-05, main → MAG2 on
  2026-04-18)
- 4 sale orders → delivery from each shop → customer invoices
  (different dates)
- A pricelist change on a MAG1 product that triggers an auto-generated
  *Proces Verbal de Schimbare Pret*
- Stock moves and account.moves are **backdated** so the historical
  retail report can be queried at past dates

## Run

```bash
./scripts/odb.sh ro19 drop demo_retail
./scripts/odb.sh ro19 create demo_retail
docker exec odoo_ro19 /opt/odoo/odoo/odoo-bin \
    -c /etc/odoo/odoo.conf -d demo_retail \
    -i l10n_ro_stock_account_retail --stop-after-init
docker exec -i odoo_ro19 /opt/odoo/odoo/odoo-bin shell \
    -c /etc/odoo/odoo.conf -d demo_retail --no-http \
    < 19.0/nexterp/l10n-romania/l10n_ro_stock_account_retail/demo/setup_demo.py
```

## Sample output

```
ACCOUNT BALANCES (current)
  371000 Merchandise                                =     54,898.80 RON
  378000 Adaos comercial - default                  =           0.00 RON
  378001 Adaos comercial - MAG1 Bucuresti           =     -3,057.41 RON
  378002 Adaos comercial - MAG2 Cluj                =     -1,524.37 RON
  442800 TVA neexigibila - default                  =           0.00 RON
  442801 TVA neexigibila - MAG1 Bucuresti           =     -1,734.65 RON
  442802 TVA neexigibila - MAG2 Cluj                =     -1,013.58 RON
  607000 Cheltuieli marfuri                         =     13,478.83 RON
  707000 Venituri marfuri                           =     -2,409.02 RON
```

The two default accounts (378000, 442800) stay at 0 — every booking
hits the location-level override.

## Historical retail report

`l10n.ro.stock.retail.report` reads from `stock.move` (filtered by
`sm.date <= at_date` when the context key `l10n_ro_retail_at_date` is
set) so it can answer "what was the stock at this past date":

```
RETAIL STOCK — NOW                       606 buc  17,636.25 retail
RETAIL STOCK AT 2026-04-10               389 buc  11,602.70 retail   (only MG1, after so1)
RETAIL STOCK AT 2026-04-25               659 buc  19,006.42 retail   (both shops, before later sales)
```

Programmatic use from anywhere:

```python
env["l10n.ro.stock.retail.report"].with_context(
    l10n_ro_retail_at_date="2026-04-25 23:59:59"
).search([])
```

Note: when running multiple historical queries in the same env, call
`env["l10n.ro.stock.retail.report"].invalidate_model()` between
queries — the row ids are derived from
`warehouse_id * 1e8 + location_id * 1e6 + product_id` (stable across
queries) so the ORM cache will return stale values otherwise.
