"""Comprehensive demo for l10n_ro_stock_account_retail.

Builds:
- Romanian company + chart of accounts + stock journal
- Stock-related accounts (371, 378.*, 4428.*, 607, 707) — including
  one 378 and one 4428 account per retail shop, set at the location
  level so the priority "location -> product -> category -> company"
  is exercised
- FIFO product category
- Two retail warehouses (MAG1 Bucuresti, MAG2 Cluj) with their own
  pricelists and location-level 378/4428 accounts
- ~30 procedurally-generated products
- 3 purchase orders (different dates) with reception in the main
  warehouse + vendor bills
- Internal transfers from the main warehouse to each retail shop on
  successive dates
- 2 sale orders + deliveries from each retail shop + customer
  invoices, on different dates so the historical report can compare
- A pricelist change that triggers an auto Proces Verbal in MAG1
- Prints balances, retail report at "now" and at three past dates
"""

import random as _random

env = env  # noqa: F821 (provided by `odoo shell`)
log = lambda *a: print("[demo]", *a)  # noqa: E731
_random.seed(42)


# -----------------------------------------------------------------------------
# Company + chart of accounts
# -----------------------------------------------------------------------------
company = env.ref("base.main_company")
company.write(
    {
        "country_id": env.ref("base.ro").id,
        "name": "NextERP Demo Retail",
        "currency_id": env.ref("base.RON").id,
    }
)
env["account.chart.template"].try_loading("ro", company=company)
company.l10n_ro_accounting = True

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

# Install purchase + sale on top
modules_to_install = env["ir.module.module"].search(
    [("name", "in", ("purchase", "sale_management", "stock_account"))]
)
to_install = modules_to_install.filtered(lambda m: m.state != "installed")
if to_install:
    to_install.button_immediate_install()
    env.registry.reset_changes()
log("Purchase + sale installed")


# -----------------------------------------------------------------------------
# Accounts
# -----------------------------------------------------------------------------
Account = env["account.account"]


def acc(code, name, kind):
    a = Account.search(
        [("company_ids", "in", company.id), ("code", "=", code)], limit=1
    )
    if not a:
        a = Account.create(
            {
                "code": code,
                "name": name,
                "account_type": kind,
                "company_ids": [(4, company.id)],
            }
        )
    return a


a_371 = acc("371000", "Marfuri", "asset_current")
a_378 = acc("378000", "Adaos comercial - default", "asset_current")
a_4428 = acc("442800", "TVA neexigibila - default", "liability_current")
a_378_b = acc("378001", "Adaos comercial - MAG1 Bucuresti", "asset_current")
a_4428_b = acc("442801", "TVA neexigibila - MAG1 Bucuresti", "liability_current")
a_378_c = acc("378002", "Adaos comercial - MAG2 Cluj", "asset_current")
a_4428_c = acc("442802", "TVA neexigibila - MAG2 Cluj", "liability_current")
a_607 = acc("607000", "Cheltuieli marfuri", "expense")
a_707 = acc("707000", "Venituri marfuri", "income")
a_4426 = acc("442600", "TVA deductibila", "asset_current")
a_4427 = acc("442700", "TVA colectata", "liability_current")

company.account_stock_valuation_id = a_371
company.l10n_ro_account_markup_id = a_378
company.l10n_ro_account_deferred_vat_id = a_4428
log("Accounts wired on company (defaults 378 / 4428)")


# -----------------------------------------------------------------------------
# Taxes
# -----------------------------------------------------------------------------
tax_sale = env["account.tax"].search(
    [
        ("company_id", "=", company.id),
        ("amount", "=", 19.0),
        ("type_tax_use", "=", "sale"),
    ],
    limit=1,
)
if not tax_sale:
    tax_sale = env["account.tax"].create(
        {
            "name": "TVA 19% (PVA)",
            "amount_type": "percent",
            "amount": 19.0,
            "type_tax_use": "sale",
            "company_id": company.id,
            "invoice_repartition_line_ids": [
                (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                (
                    0,
                    0,
                    {
                        "factor_percent": 100,
                        "repartition_type": "tax",
                        "account_id": a_4427.id,
                    },
                ),
            ],
            "refund_repartition_line_ids": [
                (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                (
                    0,
                    0,
                    {
                        "factor_percent": 100,
                        "repartition_type": "tax",
                        "account_id": a_4427.id,
                    },
                ),
            ],
        }
    )

tax_purchase = env["account.tax"].search(
    [
        ("company_id", "=", company.id),
        ("amount", "=", 19.0),
        ("type_tax_use", "=", "purchase"),
    ],
    limit=1,
)
if not tax_purchase:
    tax_purchase = env["account.tax"].create(
        {
            "name": "TVA 19% achizitie",
            "amount_type": "percent",
            "amount": 19.0,
            "type_tax_use": "purchase",
            "company_id": company.id,
            "invoice_repartition_line_ids": [
                (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                (
                    0,
                    0,
                    {
                        "factor_percent": 100,
                        "repartition_type": "tax",
                        "account_id": a_4426.id,
                    },
                ),
            ],
            "refund_repartition_line_ids": [
                (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                (
                    0,
                    0,
                    {
                        "factor_percent": 100,
                        "repartition_type": "tax",
                        "account_id": a_4426.id,
                    },
                ),
            ],
        }
    )
log("Taxes ready: sale=%s purchase=%s" % (tax_sale.name, tax_purchase.name))


# -----------------------------------------------------------------------------
# Category (FIFO)
# -----------------------------------------------------------------------------
category = env["product.category"].search(
    [("name", "=", "Marfuri Retail Demo")], limit=1
)
if not category:
    category = env["product.category"].create(
        {
            "name": "Marfuri Retail Demo",
            "property_valuation": "real_time",
            "property_cost_method": "fifo",
            "property_stock_valuation_account_id": a_371.id,
            "property_account_income_categ_id": a_707.id,
            "property_account_expense_categ_id": a_607.id,
        }
    )
log("Category ready (FIFO) — %s" % category.name)


# -----------------------------------------------------------------------------
# Warehouses
# -----------------------------------------------------------------------------
Warehouse = env["stock.warehouse"]
main_wh = Warehouse.search(
    [("company_id", "=", company.id), ("code", "=", "WH")], limit=1
)
if not main_wh:
    main_wh = Warehouse.create({"name": "Depozit Central", "code": "WH"})


def make_pricelist(name):
    pl = env["product.pricelist"].search(
        [("name", "=", name), ("company_id", "=", company.id)], limit=1
    )
    if not pl:
        pl = env["product.pricelist"].create(
            {
                "name": name,
                "currency_id": company.currency_id.id,
                "company_id": company.id,
            }
        )
    return pl


pl_buc = make_pricelist("PVA MAG1 Bucuresti")
pl_cluj = make_pricelist("PVA MAG2 Cluj")


def make_retail_wh(name, code, pricelist, loc_markup, loc_def_vat):
    wh = Warehouse.search([("code", "=", code)], limit=1)
    if not wh:
        wh = Warehouse.create({"name": name, "code": code})
    wh.write({"l10n_ro_retail": True, "l10n_ro_retail_pricelist_id": pricelist.id})
    wh.lot_stock_id.write(
        {
            "l10n_ro_account_markup_id": loc_markup.id,
            "l10n_ro_account_deferred_vat_id": loc_def_vat.id,
        }
    )
    return wh


mag1 = make_retail_wh("MAG1 Bucuresti", "MG1", pl_buc, a_378_b, a_4428_b)
mag2 = make_retail_wh("MAG2 Cluj", "MG2", pl_cluj, a_378_c, a_4428_c)
log(
    "Retail warehouses: %s (378=%s/4428=%s), %s (378=%s/4428=%s)"
    % (mag1.code, a_378_b.code, a_4428_b.code, mag2.code, a_378_c.code, a_4428_c.code)
)


# -----------------------------------------------------------------------------
# Partners
# -----------------------------------------------------------------------------
supplier = env["res.partner"].search([("name", "=", "Furnizor Demo SRL")], limit=1)
if not supplier:
    supplier = env["res.partner"].create(
        {"name": "Furnizor Demo SRL", "is_company": True, "country_id": env.ref("base.ro").id}
    )

customer = env["res.partner"].search([("name", "=", "Client Demo SRL")], limit=1)
if not customer:
    customer = env["res.partner"].create(
        {"name": "Client Demo SRL", "is_company": True, "country_id": env.ref("base.ro").id}
    )


# -----------------------------------------------------------------------------
# Products (~30) with cost + per-shop PVA
# -----------------------------------------------------------------------------
PRODUCT_NAMES = [
    "Cafea Macinata 250g", "Cafea Boabe 1kg", "Ceai Negru 100g", "Ceai Verde 100g",
    "Zahar Tos 1kg", "Faina 1kg", "Ulei Floarea Soarelui 1L", "Otet 1L",
    "Sare Mare 1kg", "Piper Negru 50g", "Lapte 1L", "Iaurt 400g",
    "Branza Telemea 500g", "Cascaval 500g", "Unt 200g", "Smantana 200g",
    "Detergent 2L", "Sapun Lichid 500ml", "Sampon 400ml", "Balsam 400ml",
    "Pasta Dinti 100ml", "Periuta Dinti", "Hartie Igienica 10buc",
    "Servetele Umede", "Detergent Vase 1L", "Burete Bucatarie",
    "Saci Menaj 30L", "Folie Aluminiu 10m", "Punga Frigider 20buc",
    "Lumanari 12buc",
]

Product = env["product.product"]
products = Product.browse()
pricelist_item_obj = env["product.pricelist.item"].with_context(
    skip_retail_price_change=True
)
for name in PRODUCT_NAMES:
    cost = round(_random.uniform(2, 30), 2)
    pva_buc = round(cost * 1.5, 2)
    pva_cluj = round(cost * 1.4, 2)
    p = Product.search([("name", "=", name)], limit=1)
    if not p:
        p = Product.create(
            {
                "name": name,
                "is_storable": True,
                "categ_id": category.id,
                "standard_price": cost,
                "list_price": pva_buc,
                "taxes_id": [(6, 0, tax_sale.ids)],
                "supplier_taxes_id": [(6, 0, tax_purchase.ids)],
                "purchase_method": "receive",
                "invoice_policy": "delivery",
            }
        )
    else:
        p.write({"standard_price": cost})
    for pl, pva in ((pl_buc, pva_buc), (pl_cluj, pva_cluj)):
        item = env["product.pricelist.item"].search(
            [("pricelist_id", "=", pl.id), ("product_id", "=", p.id)],
            limit=1,
        )
        if not item:
            pricelist_item_obj.create(
                {
                    "pricelist_id": pl.id,
                    "applied_on": "0_product_variant",
                    "product_id": p.id,
                    "compute_price": "fixed",
                    "fixed_price": pva,
                }
            )
    products |= p
log("Products created: %d" % len(products))


# -----------------------------------------------------------------------------
# Purchase orders (3 batches) with reception + bills
# -----------------------------------------------------------------------------
PurchaseOrder = env["purchase.order"]


def make_po(date_str, products_qty):
    po_lines = []
    for product, qty in products_qty:
        po_lines.append(
            (
                0,
                0,
                {
                    "product_id": product.id,
                    "product_qty": qty,
                    "price_unit": product.standard_price,
                    "tax_ids": [(6, 0, tax_purchase.ids)],
                    "date_planned": date_str,
                },
            )
        )
    po = PurchaseOrder.create(
        {
            "partner_id": supplier.id,
            "date_order": date_str,
            "picking_type_id": main_wh.in_type_id.id,
            "order_line": po_lines,
        }
    )
    po.button_confirm()
    for picking in po.picking_ids:
        picking.action_assign()
        for m in picking.move_ids:
            m.quantity = m.product_uom_qty
            m.picked = True
        picking.with_context(force_period_date=date_str)._action_done()
    picking.move_ids.write({"date": date_str})
    po.action_create_invoice()
    bill = po.invoice_ids[:1]
    bill.invoice_date = date_str
    bill.action_post()
    return po


po_dates = ["2026-04-01", "2026-04-15", "2026-04-28"]
for d in po_dates:
    qts = [(p, _random.randint(20, 60)) for p in products]
    po = make_po(d, qts)
    log("PO %s on %s: %d lines, %.2f RON" % (po.name, d, len(qts), po.amount_untaxed))


# -----------------------------------------------------------------------------
# Internal transfers main -> retail shops
# -----------------------------------------------------------------------------
def make_transfer(date_str, dest_warehouse, lines):
    picking_type = main_wh.int_type_id
    picking = env["stock.picking"].create(
        {
            "picking_type_id": picking_type.id,
            "location_id": main_wh.lot_stock_id.id,
            "location_dest_id": dest_warehouse.lot_stock_id.id,
            "company_id": company.id,
            "scheduled_date": date_str,
        }
    )
    for product, qty in lines:
        env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": qty,
                "product_uom": product.uom_id.id,
                "location_id": main_wh.lot_stock_id.id,
                "location_dest_id": dest_warehouse.lot_stock_id.id,
                "picking_id": picking.id,
                "date": date_str,
            }
        )
    picking.action_confirm()
    picking.action_assign()
    for m in picking.move_ids:
        m.quantity = m.product_uom_qty
        m.picked = True
    picking.with_context(force_period_date=date_str)._action_done()
    picking.move_ids.write({"date": date_str})
    return picking


transfer_lines_buc = [(p, _random.randint(8, 20)) for p in products]
transfer_lines_cluj = [(p, _random.randint(5, 15)) for p in products]
t1 = make_transfer("2026-04-05", mag1, transfer_lines_buc)
t2 = make_transfer("2026-04-18", mag2, transfer_lines_cluj)
log("Transfers: %s -> MAG1, %s -> MAG2" % (t1.name, t2.name))


# -----------------------------------------------------------------------------
# Sale orders + delivery + invoice from each retail shop
# -----------------------------------------------------------------------------
SaleOrder = env["sale.order"]


def make_so(date_str, warehouse, pricelist, lines):
    so_lines = []
    for product, qty in lines:
        so_lines.append(
            (
                0,
                0,
                {
                    "product_id": product.id,
                    "product_uom_qty": qty,
                    "tax_ids": [(6, 0, tax_sale.ids)],
                },
            )
        )
    so = SaleOrder.create(
        {
            "partner_id": customer.id,
            "date_order": date_str,
            "warehouse_id": warehouse.id,
            "pricelist_id": pricelist.id,
            "order_line": so_lines,
            "company_id": company.id,
        }
    )
    so.action_confirm()
    for picking in so.picking_ids:
        picking.action_assign()
        for m in picking.move_ids:
            m.quantity = m.product_uom_qty
            m.picked = True
        picking.with_context(force_period_date=date_str)._action_done()
    picking.move_ids.write({"date": date_str})
    invoice = so._create_invoices()
    invoice.invoice_date = date_str
    invoice.action_post()
    return so


so_lines_b1 = [(products[i], _random.randint(2, 5)) for i in range(0, 10)]
so_lines_b2 = [(products[i], _random.randint(1, 4)) for i in range(10, 20)]
so_lines_c1 = [(products[i], _random.randint(2, 5)) for i in range(5, 15)]
so_lines_c2 = [(products[i], _random.randint(1, 4)) for i in range(15, 25)]
so1 = make_so("2026-04-10", mag1, pl_buc, so_lines_b1)
so2 = make_so("2026-05-02", mag1, pl_buc, so_lines_b2)
so3 = make_so("2026-04-22", mag2, pl_cluj, so_lines_c1)
so4 = make_so("2026-05-10", mag2, pl_cluj, so_lines_c2)
log(
    "Sales: %s, %s (MAG1), %s, %s (MAG2)"
    % (so1.name, so2.name, so3.name, so4.name)
)


# -----------------------------------------------------------------------------
# Pricelist change -> auto Proces Verbal in MAG1
# -----------------------------------------------------------------------------
chosen = products[0]
item = env["product.pricelist.item"].search(
    [("pricelist_id", "=", pl_buc.id), ("product_id", "=", chosen.id)],
    limit=1,
)
old_price = item.fixed_price
new_price = round(old_price * 1.10, 2)
item.fixed_price = new_price
log("MAG1 pricelist %s: %s → %s" % (chosen.name, old_price, new_price))

docs = env["l10n.ro.retail.price.change"].search(
    [("warehouse_id", "=", mag1.id), ("state", "=", "draft")]
)
docs.action_post()
log("Posted PVSP: %s" % docs.mapped("name"))


# -----------------------------------------------------------------------------
# Reporting
# -----------------------------------------------------------------------------
def show_account(account, at_date=None):
    where_date = ""
    if at_date:
        where_date = " AND am.date <= %(date)s"
    env.cr.execute(
        f"""SELECT COALESCE(SUM(debit-credit),0)::float
        FROM account_move_line aml
        JOIN account_move am ON am.id = aml.move_id
        WHERE aml.account_id=%(acc)s AND aml.company_id=%(co)s
          AND am.state='posted'{where_date}""",
        {"acc": account.id, "co": company.id, "date": at_date},
    )
    return env.cr.fetchone()[0]


print()
print("=" * 78)
print("ACCOUNT BALANCES (current)")
print("=" * 78)
for a in (a_371, a_378, a_378_b, a_378_c, a_4428, a_4428_b, a_4428_c, a_607, a_707):
    print(f"  {a.code} {a.name:42s} = {show_account(a):14,.2f} RON")


def print_report(label, ctx=None):
    print()
    print("=" * 78)
    print(label)
    print("=" * 78)
    print(
        f"  {'WH':4s} {'Product':28s} {'qty':>6s} "
        f"{'value':>10s} {'markup':>10s} {'vat':>10s} {'retail':>10s}"
    )
    env["l10n.ro.stock.retail.report"].invalidate_model()
    rows = env["l10n.ro.stock.retail.report"].with_context(**(ctx or {})).search([])
    totals = {"qty": 0, "value": 0, "markup": 0, "vat": 0, "retail": 0}
    for r in rows:
        print(
            f"  {r.warehouse_id.code:4s} {r.product_id.name:28s} "
            f"{r.quantity:6.1f} {r.value_total:10.2f} "
            f"{r.markup_total:10.2f} {r.vat_total:10.2f} {r.retail_value:10.2f}"
        )
        totals["qty"] += r.quantity
        totals["value"] += r.value_total
        totals["markup"] += r.markup_total
        totals["vat"] += r.vat_total
        totals["retail"] += r.retail_value
    print(
        f"  {'TOT':4s} {'(all)':28s} {totals['qty']:6.1f} "
        f"{totals['value']:10.2f} {totals['markup']:10.2f} "
        f"{totals['vat']:10.2f} {totals['retail']:10.2f}"
    )
    print(f"  ----- {len(rows)} rows -----")


print_report("RETAIL STOCK — NOW")
print_report(
    "RETAIL STOCK AT 2026-04-10 (before MAG2 received)",
    ctx={"l10n_ro_retail_at_date": "2026-04-10 23:59:59"},
)
print_report(
    "RETAIL STOCK AT 2026-04-25 (after both received, before later sales)",
    ctx={"l10n_ro_retail_at_date": "2026-04-25 23:59:59"},
)


print()
print("=" * 78)
print("PROCESE VERBALE DE SCHIMBARE PRET")
print("=" * 78)
for d in env["l10n.ro.retail.price.change"].search([]):
    print(
        f"  {d.name:22s} state={d.state:6s} wh={d.warehouse_id.code:4s} "
        f"date={d.date} move={d.account_move_id.name or '-'}"
    )


print()
print("=" * 78)
print("PURCHASE / SALE SUMMARY")
print("=" * 78)
pos_total = sum(p.amount_total for p in env["purchase.order"].search([]))
sos_total = sum(s.amount_total for s in env["sale.order"].search([]))
print(
    "  Purchase orders: %d (total %.2f RON inc VAT)"
    % (env["purchase.order"].search_count([]), pos_total)
)
print(
    "  Sale orders:     %d (total %.2f RON inc VAT)"
    % (env["sale.order"].search_count([]), sos_total)
)
print(
    "  Quants on hand:  %d distinct rows"
    % env["stock.quant"].search_count([("quantity", ">", 0)])
)

env.cr.commit()
log("Demo committed.")
