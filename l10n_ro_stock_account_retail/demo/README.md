# Demo script for `l10n_ro_stock_account_retail`

`setup_demo.py` builds a runnable end-to-end demo: Romanian chart of
accounts, two retail products, opening stock, transfer from main
warehouse to a retail warehouse, a retail sale, and an automatic
*Proces Verbal de Schimbare Pret* triggered by a pricelist change.

## How to run

The script is meant to be piped into `odoo-bin shell` (not loaded as
Odoo demo data — it intentionally posts stock moves and account.moves
at runtime).

```bash
# 1. Create an empty database
./scripts/odb.sh ro19 create demo_retail

# 2. Install the module (pulls in l10n_ro, l10n_ro_stock_account, etc.)
docker exec odoo_ro19 /opt/odoo/odoo/odoo-bin \
    -c /etc/odoo/odoo.conf -d demo_retail \
    -i l10n_ro_stock_account_retail --stop-after-init

# 3. Run the demo
docker cp \
    /home/nexterp/odoo/nexterp_dev/19.0/nexterp/l10n-romania/l10n_ro_stock_account_retail/demo/setup_demo.py \
    odoo_ro19:/tmp/setup_demo.py
docker exec -i odoo_ro19 /opt/odoo/odoo/odoo-bin shell \
    -c /etc/odoo/odoo.conf -d demo_retail --no-http \
    < /home/nexterp/odoo/nexterp_dev/19.0/nexterp/l10n-romania/l10n_ro_stock_account_retail/demo/setup_demo.py
```

## What gets created

- Company set to Romania (RON, country_id=base.ro), Romanian accounting
  enabled, Romanian chart of accounts loaded
- Stock journal `STJ` set as `company.account_stock_journal_id`
- Accounts `371000`, `378000`, `442800`, `607000`, `707000` (created
  if missing); `378`/`4428` wired as company defaults
- Sale tax `TVA 19% (PVA)`, tax-excluded (Odoo convention — the
  customer-visible PVA-with-VAT is computed via `taxes.compute_all`)
- Category `Marfuri Demo` valued at average cost, with stock val =
  `371000`, expense = `607000`, income = `707000`
- Pricelist `PVA Magazin Centru` with fixed-price items for each
  product
- Two products: Cafea Macinata (cost 20, PVA 30 ex-VAT = 35.70 incl),
  Detergent 2L (cost 18, PVA 25 ex-VAT = 29.75 incl)
- Two warehouses: `WH` (Depozit Central) and `MAG` (Magazin Centru,
  retail, pricelist linked)

## What gets posted

| Step | Doc | Effect |
|------|-----|--------|
| Opening stock | `STJ/.../0001-2` | inventory adjustment 100/100 in WH |
| Internal transfer 30+30 → MAG | `WH/INT/00001` | cost moved via 482; markup booked at MAG entry |
| Sale of 5 cafea | `MAG/OUT/00001` | 607 += cost; markup reversed (storno) |
| Pricelist update detergent 25 → 27 ex-VAT | auto | a draft `PVSP/2026/00001` is created by the hook |
| Posting the proces verbal | `STJ/.../0008` | books the markup / VAT delta for the 30 buc on hand |

## Expected balances

```
371000 Marfuri                = 3,376.40 RON
378000 Diferente de pret      =  -520.00 RON  (credit: adaos pe stoc)
442800 TVA neexigibila        =  -296.40 RON  (credit)
607000 Cheltuieli marfuri     = -2,560.00 RON
```

Verification:
- 378 credit = 25 buc cafea × 10 + 30 buc detergent × 9 (after PVSP)
  = 250 + 270 = 520 ✓
- 4428 credit = 25 × 5.70 + 30 × 5.13 = 142.5 + 153.9 = 296.4 ✓
