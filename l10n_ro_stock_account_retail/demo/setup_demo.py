"""Demo data for l10n_ro_stock_account_retail.

Builds end-to-end:
- Activates Romanian accounting + sets stock journal
- Creates 378 / 4428 accounts as defaults on the company
- Creates a retail pricelist + retail warehouse (Magazin Centru)
- Creates two products with cost & retail price
- Posts opening stock in the non-retail warehouse (cost only)
- Transfers stock to the retail warehouse (markup booked)
- Sells one product from retail (markup reversed)
- Changes the retail price via a Proces Verbal de Schimbare Pret
- Prints all generated account.moves


./scripts/odb.sh ro19 drop demo_retail
./scripts/odb.sh ro19 create demo_retail
docker exec odoo_ro19 /opt/odoo/odoo/odoo-bin \
    -c /etc/odoo/odoo.conf -d demo_retail \
    -i l10n_ro_stock_account_retail --stop-after-init
docker exec -i odoo_ro19 /opt/odoo/odoo/odoo-bin shell \
    -c /etc/odoo/odoo.conf -d demo_retail --no-http \
    < 19.0/nexterp/l10n-romania/l10n_ro_stock_account_retail/demo/setup_demo.py

"""

env = env  # noqa: F821 (provided by `odoo shell`)
log = lambda *a: print("[demo]", *a)  # noqa: E731

company = env.ref("base.main_company")
company.write(
    {
        "country_id": env.ref("base.ro").id,
        "name": "NextERP Demo Retail",
        "currency_id": env.ref("base.RON").id,
    }
)
# Install Romanian chart of accounts
env["account.chart.template"].try_loading("ro", company=company)
# Mark company as Romanian accounting
company.l10n_ro_accounting = True

# Stock journal — required by l10n_ro_stock_account
journal = env["account.journal"].search(
    [("company_id", "=", company.id), ("code", "=", "STJ")], limit=1
)
if not journal:
    journal = env["account.journal"].create(
        {
            "name": "Stock Journal",
            "code": "STJ",
            "type": "general",
            "company_id": company.id,
        }
    )
company.account_stock_journal_id = journal

# Helper to get/create an account
Account = env["account.account"]


def get_or_create_account(code, name, account_type):
    acc = Account.search(
        [("company_ids", "in", company.id), ("code", "=", code)], limit=1
    )
    if not acc:
        acc = Account.create(
            {
                "code": code,
                "name": name,
                "account_type": account_type,
                "company_ids": [(4, company.id)],
            }
        )
    return acc


account_371 = get_or_create_account("371000", "Marfuri", "asset_current")
account_378 = get_or_create_account(
    "378000", "Diferente de pret la marfuri", "asset_current"
)
account_4428 = get_or_create_account(
    "442800", "TVA neexigibila", "liability_current"
)
account_607 = get_or_create_account("607000", "Cheltuieli marfuri", "expense")
account_707 = get_or_create_account("707000", "Venituri marfuri", "income")

company.account_stock_valuation_id = account_371
company.l10n_ro_account_markup_id = account_378
company.l10n_ro_account_deferred_vat_id = account_4428
log("Accounts wired on company")

# Tax 19% VAT, price-included for retail
tax_19 = env["account.tax"].search(
    [
        ("company_id", "=", company.id),
        ("amount", "=", 19.0),
        ("type_tax_use", "=", "sale"),
    ],
    limit=1,
)
if not tax_19:
    tax_19 = env["account.tax"].create(
        {
            "name": "TVA 19% (PVA)",
            "amount_type": "percent",
            "amount": 19.0,
            "type_tax_use": "sale",
            "company_id": company.id,
        }
    )
log("Sale tax: %s" % tax_19.name)

# Marfuri category — using Avg cost so transfer values are stable
category = env["product.category"].search(
    [("name", "=", "Marfuri Demo")], limit=1
)
if not category:
    category = env["product.category"].create(
        {
            "name": "Marfuri Demo",
            "property_valuation": "real_time",
            "property_cost_method": "average",
            "property_stock_valuation_account_id": account_371.id,
            "property_account_income_categ_id": account_707.id,
            "property_account_expense_categ_id": account_607.id,
        }
    )

# Retail pricelist
pricelist = env["product.pricelist"].search(
    [("name", "=", "PVA Magazin Centru"), ("company_id", "=", company.id)],
    limit=1,
)
if not pricelist:
    pricelist = env["product.pricelist"].create(
        {
            "name": "PVA Magazin Centru",
            "currency_id": company.currency_id.id,
            "company_id": company.id,
        }
    )

# Two products
def make_product(name, cost, pva_no_vat):
    """Pricelist stores tax-excluded prices (Odoo convention).
    The customer-facing PVA-with-VAT = pva_no_vat * 1.19."""
    p = env["product.product"].search([("name", "=", name)], limit=1)
    if not p:
        p = env["product.product"].create(
            {
                "name": name,
                "is_storable": True,
                "categ_id": category.id,
                "standard_price": cost,
                "list_price": pva_no_vat,
                "taxes_id": [(6, 0, tax_19.ids)],
            }
        )
    else:
        p.write({"standard_price": cost, "list_price": pva_no_vat})
    item = env["product.pricelist.item"].search(
        [
            ("pricelist_id", "=", pricelist.id),
            ("product_id", "=", p.id),
        ],
        limit=1,
    )
    if not item:
        env["product.pricelist.item"].with_context(
            skip_retail_price_change=True
        ).create(
            {
                "pricelist_id": pricelist.id,
                "applied_on": "0_product_variant",
                "product_id": p.id,
                "compute_price": "fixed",
                "fixed_price": pva_no_vat,
            }
        )
    return p


# PVA cu TVA: cafea 35.70 RON, detergent 29.75 RON
product_a = make_product("Cafea Macinata 250g", cost=20.0, pva_no_vat=30.0)
product_b = make_product("Detergent 2L", cost=18.0, pva_no_vat=25.0)
log("Products: %s, %s" % (product_a.display_name, product_b.display_name))

# Warehouses
Warehouse = env["stock.warehouse"]
main_wh = Warehouse.search(
    [("company_id", "=", company.id), ("code", "=", "WH")], limit=1
)
if not main_wh:
    main_wh = Warehouse.create({"name": "Depozit Central", "code": "WH"})

retail_wh = Warehouse.search([("code", "=", "MAG")], limit=1)
if not retail_wh:
    retail_wh = Warehouse.create(
        {
            "name": "Magazin Centru",
            "code": "MAG",
            "l10n_ro_retail": True,
            "l10n_ro_retail_pricelist_id": pricelist.id,
        }
    )
else:
    retail_wh.write(
        {"l10n_ro_retail": True, "l10n_ro_retail_pricelist_id": pricelist.id}
    )
log("Warehouses: main=%s retail=%s" % (main_wh.name, retail_wh.name))


# Opening stock in MAIN warehouse (at cost) via inventory adjustment
def set_inventory(product, location, qty):
    quant = env["stock.quant"].with_context(inventory_mode=True).create(
        {
            "product_id": product.id,
            "location_id": location.id,
            "inventory_quantity": qty,
        }
    )
    quant.action_apply_inventory()


set_inventory(product_a, main_wh.lot_stock_id, 100)
set_inventory(product_b, main_wh.lot_stock_id, 100)
log("Opening stock 100/100 set in main warehouse")


# Internal transfer 30 of each from main → retail (cross-warehouse, uses transit)
picking_type = env["stock.picking.type"].search(
    [
        ("default_location_src_id.warehouse_id", "=", main_wh.id),
        ("default_location_dest_id.warehouse_id", "=", retail_wh.id),
    ],
    limit=1,
)
if not picking_type:
    # Direct transfer via custom picking, src=main, dest=retail
    picking_type = main_wh.int_type_id
picking = env["stock.picking"].create(
    {
        "picking_type_id": picking_type.id,
        "location_id": main_wh.lot_stock_id.id,
        "location_dest_id": retail_wh.lot_stock_id.id,
        "company_id": company.id,
    }
)
for p in (product_a, product_b):
    env["stock.move"].create(
        {
            "product_id": p.id,
            "product_uom_qty": 30,
            "product_uom": p.uom_id.id,
            "location_id": main_wh.lot_stock_id.id,
            "location_dest_id": retail_wh.lot_stock_id.id,
            "picking_id": picking.id,
        }
    )
picking.action_confirm()
picking.action_assign()
for m in picking.move_ids:
    m.quantity = 30
    m.picked = True
picking._action_done()
log("Transfer to retail done: picking=%s" % picking.name)


# Sale (delivery) from retail: 5 of product_a → customer
customer_loc = env.ref("stock.stock_location_customers")
sale_picking = env["stock.picking"].create(
    {
        "picking_type_id": retail_wh.out_type_id.id,
        "location_id": retail_wh.lot_stock_id.id,
        "location_dest_id": customer_loc.id,
        "company_id": company.id,
    }
)
env["stock.move"].create(
    {
        "product_id": product_a.id,
        "product_uom_qty": 5,
        "product_uom": product_a.uom_id.id,
        "location_id": retail_wh.lot_stock_id.id,
        "location_dest_id": customer_loc.id,
        "picking_id": sale_picking.id,
    }
)
sale_picking.action_confirm()
sale_picking.action_assign()
for m in sale_picking.move_ids:
    m.quantity = 5
    m.picked = True
sale_picking._action_done()
log("Retail sale done: picking=%s" % sale_picking.name)


# Trigger an auto-generated Proces Verbal de Schimbare Pret by changing PVA
item = env["product.pricelist.item"].search(
    [
        ("pricelist_id", "=", pricelist.id),
        ("product_id", "=", product_b.id),
    ],
    limit=1,
)
item.fixed_price = 27.0  # was 25 (no VAT) → PVA 32.13 incl VAT
log("Pricelist item for %s updated → %s" % (product_b.name, item.fixed_price))


# Post the auto-created draft Proces Verbal
docs = env["l10n.ro.retail.price.change"].search(
    [("warehouse_id", "=", retail_wh.id), ("state", "=", "draft")]
)
log("Draft proces verbal docs: %s" % docs.mapped("name"))
docs.action_post()
log("Posted price change docs: %s" % docs.mapped("name"))


# Summary
def show_account(account):
    env.cr.execute(
        """SELECT COALESCE(SUM(debit-credit),0)::float
        FROM account_move_line aml
        JOIN account_move am ON am.id = aml.move_id
        WHERE aml.account_id=%s AND aml.company_id=%s AND am.state='posted'""",
        (account.id, company.id),
    )
    return env.cr.fetchone()[0]


print()
print("=" * 70)
print("ACCOUNT BALANCES")
print("=" * 70)
for acc in (account_371, account_378, account_4428, account_607, account_707):
    print(f"  {acc.code} {acc.name:35s} = {show_account(acc):12,.2f} RON")

print()
print("=" * 70)
print("ON-HAND RETAIL STOCK (l10n.ro.stock.retail.report)")
print("=" * 70)
rows = env["l10n.ro.stock.retail.report"].search([])
for r in rows:
    print(
        f"  {r.product_id.display_name:30s} qty={r.quantity:6.1f}  "
        f"cost={r.cost_total:8.2f}  markup={r.markup_total:8.2f}  "
        f"vat={r.vat_total:8.2f}  pva={r.retail_value:8.2f}"
    )

print()
print("=" * 70)
print("ACCOUNT MOVES (last 20)")
print("=" * 70)
moves = env["account.move"].search([("state", "=", "posted")], order="id desc", limit=20)
for m in moves:
    print(f"  {m.name:25s}  {m.date}  ref={m.ref or '-'}")
    for aml in m.line_ids:
        d = aml.debit or 0
        c = aml.credit or 0
        print(
            f"      {aml.account_id.code:8s} D={d:10,.2f}  C={c:10,.2f}  "
            f"{aml.name or ''}"
        )

print()
print("=" * 70)
print("PROCES VERBAL DE SCHIMBARE PRET")
print("=" * 70)
for d in env["l10n.ro.retail.price.change"].search([]):
    print(
        f"  {d.name:25s} state={d.state} wh={d.warehouse_id.code} "
        f"date={d.date} move={d.account_move_id.name or '-'}"
    )

env.cr.commit()
