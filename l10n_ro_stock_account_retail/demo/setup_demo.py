# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
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

# pylint: disable=print-used
import random as _random

from odoo.exceptions import UserError

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
a_371_b = acc("371001", "Marfuri - MAG1 Bucuresti", "asset_current")
a_371_c = acc("371002", "Marfuri - MAG2 Cluj", "asset_current")
a_607 = acc("607000", "Cheltuieli marfuri", "expense")
a_607_b = acc("607001", "Cheltuieli marfuri - MAG1 Bucuresti", "expense")
a_607_c = acc("607002", "Cheltuieli marfuri - MAG2 Cluj", "expense")
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
log(f"Taxes ready: sale={tax_sale.name} purchase={tax_purchase.name}")


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
            # Without this the base module never looks at the location
            # accounts, and a depot to shop transfer books the goods to 607 as
            # if they had been consumed instead of moving them to the shop's
            # own 371.
            "l10n_ro_stock_account_change": True,
            "property_cost_method": "fifo",
            "property_stock_valuation_account_id": a_371.id,
            "property_account_income_categ_id": a_707.id,
            "property_account_expense_categ_id": a_607.id,
        }
    )
log(f"Category ready (FIFO) — {category.name}")


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


def make_retail_wh(
    name, code, pricelist, loc_markup, loc_def_vat, loc_stock, loc_expense
):
    wh = Warehouse.search([("code", "=", code)], limit=1)
    if not wh:
        wh = Warehouse.create({"name": name, "code": code})
    wh.write({"l10n_ro_retail": True, "l10n_ro_retail_pricelist_id": pricelist.id})
    wh.lot_stock_id.write(
        {
            # Its own 371 and 607, so a transfer into the shop debits the
            # shop's stock account rather than the company default, and each
            # shop can be reconciled on its own.
            "l10n_ro_property_stock_valuation_account_id": loc_stock.id,
            "l10n_ro_property_account_expense_location_id": loc_expense.id,
            "l10n_ro_account_markup_id": loc_markup.id,
            "l10n_ro_account_deferred_vat_id": loc_def_vat.id,
        }
    )
    return wh


mag1 = make_retail_wh(
    "MAG1 Bucuresti", "MG1", pl_buc, a_378_b, a_4428_b, a_371_b, a_607_b
)
mag2 = make_retail_wh("MAG2 Cluj", "MG2", pl_cluj, a_378_c, a_4428_c, a_371_c, a_607_c)
log(
    f"Retail warehouses: {mag1.code} (378={a_378_b.code}/4428={a_4428_b.code}), "
    f"{mag2.code} (378={a_378_c.code}/4428={a_4428_c.code})"
)


# -----------------------------------------------------------------------------
# Partners
# -----------------------------------------------------------------------------
supplier = env["res.partner"].search([("name", "=", "Furnizor Demo SRL")], limit=1)
if not supplier:
    supplier = env["res.partner"].create(
        {
            "name": "Furnizor Demo SRL",
            "is_company": True,
            "country_id": env.ref("base.ro").id,
        }
    )

customer = env["res.partner"].search([("name", "=", "Client Demo SRL")], limit=1)
if not customer:
    customer = env["res.partner"].create(
        {
            "name": "Client Demo SRL",
            "is_company": True,
            "country_id": env.ref("base.ro").id,
        }
    )


# -----------------------------------------------------------------------------
# Products (~30) with cost + per-shop PVA
# -----------------------------------------------------------------------------
PRODUCT_NAMES = [
    "Cafea Macinata 250g",
    "Cafea Boabe 1kg",
    "Ceai Negru 100g",
    "Ceai Verde 100g",
    "Zahar Tos 1kg",
    "Faina 1kg",
    "Ulei Floarea Soarelui 1L",
    "Otet 1L",
    "Sare Mare 1kg",
    "Piper Negru 50g",
    "Lapte 1L",
    "Iaurt 400g",
    "Branza Telemea 500g",
    "Cascaval 500g",
    "Unt 200g",
    "Smantana 200g",
    "Detergent 2L",
    "Sapun Lichid 500ml",
    "Sampon 400ml",
    "Balsam 400ml",
    "Pasta Dinti 100ml",
    "Periuta Dinti",
    "Hartie Igienica 10buc",
    "Servetele Umede",
    "Detergent Vase 1L",
    "Burete Bucatarie",
    "Saci Menaj 30L",
    "Folie Aluminiu 10m",
    "Punga Frigider 20buc",
    "Lumanari 12buc",
]

Product = env["product.product"]
products = Product.browse()
pricelist_item_obj = env["product.pricelist.item"].with_context(
    skip_retail_price_change=True
)
for name in PRODUCT_NAMES:
    cost = round(_random.uniform(2, 30), 2)
    # Shelf prices are held VAT included: a 50% (resp. 40%) markup on the cost,
    # plus the VAT that sits inside the price the customer pays.
    pva_buc = round(cost * 1.5 * 1.19, 2)
    pva_cluj = round(cost * 1.4 * 1.19, 2)
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
log(f"Products created: {len(products)}")


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
    log(f"PO {po.name} on {d}: {len(qts)} lines, {po.amount_untaxed:.2f} RON")


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
log(f"Transfers: {t1.name} -> MAG1, {t2.name} -> MAG2")


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
log(f"Sales: {so1.name}, {so2.name} (MAG1), {so3.name}, {so4.name} (MAG2)")


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
log(f"MAG1 pricelist {chosen.name}: {old_price} → {new_price}")

docs = env["l10n.ro.retail.price.change"].search(
    [("warehouse_id", "=", mag1.id), ("state", "=", "draft")]
)
docs.action_post()
log(f"Posted PVSP: {docs.mapped('name')}")


# -----------------------------------------------------------------------------
# Helpers shared by the case sections below
# -----------------------------------------------------------------------------
installed_modules = set(
    env["ir.module.module"].search([("state", "=", "installed")]).mapped("name")
)


def make_transfer_to_location(date_str, src_location, dest_location, lines):
    """A done internal transfer between two explicit locations."""
    picking = env["stock.picking"].create(
        {
            "picking_type_id": main_wh.int_type_id.id,
            "location_id": src_location.id,
            "location_dest_id": dest_location.id,
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
                "location_id": src_location.id,
                "location_dest_id": dest_location.id,
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


def make_transfer_between(date_str, src_warehouse, dest_warehouse, lines):
    return make_transfer_to_location(
        date_str, src_warehouse.lot_stock_id, dest_warehouse.lot_stock_id, lines
    )


def make_return(picking, date_str, ratio=1.0):
    """Return part of a done picking, through the standard return wizard, so
    ``origin_returned_move_id`` is set and the retail legs settle against the
    original move rather than against today's price."""
    wizard = (
        env["stock.return.picking"]
        .with_context(active_id=picking.id, active_model="stock.picking")
        .create({})
    )
    for line in wizard.product_return_moves:
        line.quantity = max(round(line.quantity * ratio, 2), 1.0)
    result = wizard.action_create_returns()
    ret = env["stock.picking"].browse(result["res_id"])
    ret.action_assign()
    for m in ret.move_ids:
        m.quantity = m.product_uom_qty
        m.picked = True
    ret.with_context(force_period_date=date_str)._action_done()
    ret.move_ids.write({"date": date_str})
    return ret


def make_po_into(date_str, warehouse, products_qty):
    """A purchase order received straight into a warehouse, not billed yet."""
    po = PurchaseOrder.create(
        {
            "partner_id": supplier.id,
            "date_order": date_str,
            "picking_type_id": warehouse.in_type_id.id,
            "order_line": [
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
                for product, qty in products_qty
            ],
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
    return po


# -----------------------------------------------------------------------------
# Case: manual Proces Verbal (the auto one above came from a pricelist change)
# -----------------------------------------------------------------------------
if "l10n.ro.retail.price.change" in env:
    pv = env["l10n.ro.retail.price.change"].create({"warehouse_id": mag2.id})
    pv.action_load_products()
    for line in pv.line_ids[:5]:
        line.new_price_with_vat = round(line.old_price_with_vat * 1.15, 2)
    pv.action_post()
    log(
        f"Manual price change {pv.name}: {len(pv.line_ids)} lines, "
        f"markup delta {sum(pv.line_ids.mapped('markup_diff_total')):.2f}"
    )


# -----------------------------------------------------------------------------
# Case: transfer between two shops - source releases its markup at its own
# shelf price, destination loads its own
# -----------------------------------------------------------------------------
shop_to_shop = make_transfer_between(
    "2026-05-12", mag1, mag2, [(products[i], 2) for i in range(0, 5)]
)
log(f"Shop to shop transfer: {shop_to_shop.name} MAG1 -> MAG2")


# -----------------------------------------------------------------------------
# Case: transfer back from a shop to the depot - the markup comes off, the
# goods go back to being valued at cost
# -----------------------------------------------------------------------------
shop_to_depot = make_transfer_between(
    "2026-05-14", mag1, main_wh, [(products[i], 1) for i in range(5, 9)]
)
log(f"Shop to depot transfer: {shop_to_depot.name} MAG1 -> WH")


# -----------------------------------------------------------------------------
# Case: customer return into a shop - puts back exactly what the sale released,
# not what today's pricelist would say
# -----------------------------------------------------------------------------
sale_picking = so1.picking_ids.filtered(lambda p: p.state == "done")[:1]
sale_return = make_return(sale_picking, "2026-05-16", ratio=0.5)
log(f"Customer return into MAG1: {sale_return.name}")


# -----------------------------------------------------------------------------
# Case: purchase return out of a shop
# -----------------------------------------------------------------------------
shop_reception = env["stock.picking"].search(
    [
        ("location_dest_id", "=", mag1.lot_stock_id.id),
        ("state", "=", "done"),
        ("picking_type_id.code", "=", "internal"),
    ],
    limit=1,
)
if shop_reception:
    purchase_return = make_return(shop_reception, "2026-05-18", ratio=0.25)
    log(f"Return out of MAG1: {purchase_return.name}")


# -----------------------------------------------------------------------------
# Case: a shelf inside MAG1 with its own 378/4428, so the parent walk is
# exercised: the shelf inherits nothing of its own and must resolve upwards
# -----------------------------------------------------------------------------
shelf = env["stock.location"].search(
    [("name", "=", "Raft Bauturi"), ("location_id", "=", mag1.lot_stock_id.id)],
    limit=1,
)
if not shelf:
    shelf = env["stock.location"].create(
        {
            "name": "Raft Bauturi",
            "usage": "internal",
            "location_id": mag1.lot_stock_id.id,
        }
    )
shelf_move = make_transfer_to_location(
    "2026-05-20", main_wh.lot_stock_id, shelf, [(products[10], 3)]
)
log(
    f"Transfer into sublocation {shelf.display_name}: {shelf_move.name}; "
    f"markup account resolved = "
    f"{shelf._l10n_ro_get_markup_account(product=products[10]).code}"
)


# -----------------------------------------------------------------------------
# Case: a clearance shop that is allowed to sell below cost
# -----------------------------------------------------------------------------
pl_outlet = make_pricelist("PVA MAG3 Outlet")
outlet = make_retail_wh("MAG3 Outlet", "MG3", pl_outlet, a_378, a_4428, a_371, a_607)
outlet.l10n_ro_retail_allow_negative_markup = True
clearance = products[20]
outlet_item = (
    env["product.pricelist.item"]
    .with_context(skip_retail_price_change=True)
    .create(
        {
            "pricelist_id": pl_outlet.id,
            "applied_on": "0_product_variant",
            "product_id": clearance.id,
            "compute_price": "fixed",
            # Deliberately under cost: this is what the flag is for.
            "fixed_price": round(clearance.standard_price * 0.8, 2),
        }
    )
)
outlet_move = make_transfer_between("2026-05-22", main_wh, outlet, [(clearance, 5)])
outlet_markup, _outlet_vat = env["l10n.ro.retail.markup.line"]._l10n_ro_carried(
    outlet, clearance, company
)
log(
    f"Clearance shop {outlet.code}: {clearance.name} at "
    f"{outlet_item.fixed_price} against a cost of "
    f"{clearance.standard_price:.2f} -> markup {outlet_markup:.2f}"
)


# -----------------------------------------------------------------------------
# Case: landed cost on goods held in a shop - 371 stays put, the markup drops.
# Shown twice: one that fits inside the markup, and one that does not and is
# therefore refused, which is the whole point of the guard.
# -----------------------------------------------------------------------------
if "l10n_ro_stock_account_retail_landed_cost" in installed_modules:
    lc_product = env["product.product"].search(
        [("name", "=", "Transport marfa")], limit=1
    )
    if not lc_product:
        lc_product = env["product.product"].create(
            {
                "name": "Transport marfa",
                "type": "service",
                "is_storable": False,
                "landed_cost_ok": True,
                "standard_price": 0.0,
            }
        )
    # A reception of its own, so the markup is whole and the arithmetic is
    # readable rather than whatever is left of an earlier picking.
    lc_item = products[3]
    lc_po = make_po_into("2026-05-24", mag1, [(lc_item, 20)])
    lc_picking = lc_po.picking_ids[:1]

    def make_landed_cost(amount, date_str):
        cost = env["stock.landed.cost"].create(
            {
                "company_id": company.id,
                "date": date_str,
                "picking_ids": [(6, 0, lc_picking.ids)],
                "account_journal_id": journal.id,
                "cost_lines": [
                    (
                        0,
                        0,
                        {
                            "product_id": lc_product.id,
                            "price_unit": amount,
                            "split_method": "equal",
                            "account_id": a_607.id,
                        },
                    )
                ],
            }
        )
        cost.compute_landed_cost()
        return cost

    Ledger = env["l10n.ro.retail.markup.line"]
    before_markup, _ = Ledger._l10n_ro_carried(mag1, lc_item, company)
    small = make_landed_cost(round(before_markup * 0.25, 2), "2026-05-24")
    small.button_validate()
    after_markup, _ = Ledger._l10n_ro_carried(mag1, lc_item, company)
    log(
        f"Landed cost {small.name} of {small.amount_total:.2f} on "
        f"{lc_item.name}: markup {before_markup:.2f} -> {after_markup:.2f}, "
        f"371 unchanged"
    )

    # Now one bigger than what is left of the markup. It has to be refused,
    # naming the price rise that would make it work.
    oversized = make_landed_cost(round(after_markup * 3, 2), "2026-05-25")
    try:
        oversized.button_validate()
    except UserError as exc:
        log(f"Oversized landed cost correctly refused: {exc.args[0].splitlines()[0]}")
    else:
        log("WARNING: an oversized landed cost was accepted")


# -----------------------------------------------------------------------------
# Case: a vendor bill above the reception price - the difference lands on the
# markup, and the confirmation wizard says so before it is posted
# -----------------------------------------------------------------------------
if "l10n_ro_stock_account_retail_price_difference" in installed_modules:
    company.l10n_ro_stock_acc_price_diff = True
    pd_product = products[1]
    pd_po = make_po_into("2026-05-26", mag1, [(pd_product, 10)])
    pd_po.action_create_invoice()
    pd_bill = pd_po.invoice_ids[:1]
    pd_bill.invoice_date = "2026-05-26"
    for line in pd_bill.invoice_line_ids:
        line.price_unit = round(line.price_unit * 1.20, 2)
    pd_bill.with_context(l10n_ro_approved_price_difference=True).action_post()
    pd_markup, _pd_vat = env["l10n.ro.retail.markup.line"]._l10n_ro_carried(
        mag1, pd_product, company
    )
    log(
        f"Vendor bill {pd_bill.name} 20% above reception on "
        f"{pd_product.name}; markup now {pd_markup:.2f}"
    )


# -----------------------------------------------------------------------------
# Case: a point of sale session on MAG1, opened, sold through and closed
# -----------------------------------------------------------------------------
if "l10n_ro_stock_account_retail_pos" in installed_modules:
    # `open_ui` refuses the superuser outright, and `odoo shell` is the
    # superuser, so the whole block runs as the admin user instead.
    pos_user = env.ref("base.user_admin")
    pos_user.group_ids |= env.ref("point_of_sale.group_pos_manager")
    penv = env(user=pos_user)

    cash_journal = penv["account.journal"].search(
        [("company_id", "=", company.id), ("type", "=", "cash")], limit=1
    ) or penv["account.journal"].create(
        {
            "name": "Casa MAG1",
            "code": "CSH1",
            "type": "cash",
            "company_id": company.id,
        }
    )
    method = penv["pos.payment.method"].search(
        [("name", "=", "Numerar MAG1")], limit=1
    ) or penv["pos.payment.method"].create(
        {
            "name": "Numerar MAG1",
            "journal_id": cash_journal.id,
            "company_id": company.id,
        }
    )
    pos_config = penv["pos.config"].search([("name", "=", "Casa MAG1")], limit=1)
    if not pos_config:
        pos_config = penv["pos.config"].create(
            {
                "name": "Casa MAG1",
                "company_id": company.id,
                "picking_type_id": mag1.pos_type_id.id,
                "payment_method_ids": [(6, 0, method.ids)],
            }
        )
    pos_config.open_ui()
    pos_session = pos_config.current_session_id
    pos_product = products[2]
    pos_price = pos_product.with_context(pricelist=pl_buc.id).lst_price or 10.0
    pos_total = round(pos_price * 3, 2)
    pos_order = penv["pos.order"].create(
        {
            "company_id": company.id,
            "session_id": pos_session.id,
            "partner_id": customer.id,
            "lines": [
                (
                    0,
                    0,
                    {
                        "product_id": pos_product.id,
                        "qty": 3,
                        "price_unit": pos_price,
                        "price_subtotal": pos_total,
                        "price_subtotal_incl": pos_total,
                    },
                )
            ],
            "amount_tax": 0.0,
            "amount_total": pos_total,
            "amount_paid": 0.0,
            "amount_return": 0.0,
            "last_order_preparation_change": "{}",
        }
    )
    penv["pos.make.payment"].with_context(
        active_ids=pos_order.ids, active_id=pos_order.id
    ).create({"amount": pos_total, "payment_method_id": method.id}).check()
    pos_session.action_pos_session_closing_control()
    closing_accounts = sorted(
        set(pos_session.move_id.line_ids.account_id.mapped("code"))
    )
    stock_codes = {a_371.code, a_607.code}
    log(
        f"POS session {pos_session.name} closed after selling 3 x "
        f"{pos_product.name}; closing entry touches {closing_accounts} - "
        f"stock accounts present: {sorted(stock_codes & set(closing_accounts))}"
    )


# -----------------------------------------------------------------------------
# Case: both printable documents actually render
# -----------------------------------------------------------------------------
Report = env["ir.actions.report"]
if "l10n.ro.retail.price.change" in env:
    posted_pv = env["l10n.ro.retail.price.change"].search(
        [("state", "=", "done")], limit=1
    )
    if posted_pv:
        html = Report._render_qweb_html(
            "l10n_ro_stock_account_retail_price_change."
            "action_report_retail_price_change",
            posted_pv.ids,
        )[0]
        log(f"Price change report renders: {len(html)} bytes for {posted_pv.name}")
if "l10n_ro_stock_account_retail_picking_report" in installed_modules:
    nir = env["stock.picking"].search(
        [("l10n_ro_retail_incoming", "=", True), ("state", "=", "done")], limit=1
    )
    if nir:
        html = Report._render_qweb_html("stock.action_report_delivery", nir.ids)[0]
        log(f"Goods receipt note renders: {len(html)} bytes for {nir.name}")


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
        f"{'cost':>10s} {'markup':>10s} {'vat':>10s} {'371':>10s}"
    )
    env["l10n.ro.stock.retail.report"].invalidate_model()
    rows = env["l10n.ro.stock.retail.report"].with_context(**(ctx or {})).search([])
    totals = {"qty": 0, "value": 0, "markup": 0, "vat": 0, "retail": 0}
    for r in rows:
        print(
            f"  {r.warehouse_id.code:4s} {r.product_id.name:28s} "
            f"{r.quantity:6.1f} {r.cost_total:10.2f} "
            f"{r.markup_total:10.2f} {r.vat_total:10.2f} {r.retail_value:10.2f}"
        )
        totals["qty"] += r.quantity
        totals["value"] += r.cost_total
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

# The ledger is dated and carries the cost as well as the markup, so the same
# report answers for any past moment. These are the figures to put next to the
# trial balance for 371, 378 and 4428 at that date.
for at_date in ("2026-04-10", "2026-04-25", "2026-05-15"):
    print_report(
        f"RETAIL STOCK — AS OF {at_date}",
        ctx={"l10n_ro_retail_date_to": f"{at_date} 23:59:59"},
    )

# And over a stretch of time, which is where the movements show up rather
# than only what is left at the end.
print()
print("=" * 78)
print("RETAIL STOCK — MOVEMENTS IN MAY 2026")
print("=" * 78)
print(
    f"  {'WH':4s} {'Product':24s} {'open':>9s} {'in':>9s} "
    f"{'out':>9s} {'corr':>9s} {'close':>9s}"
)
period = env["l10n.ro.stock.retail.report"].with_context(
    l10n_ro_retail_date_from="2026-05-01 00:00:00",
    l10n_ro_retail_date_to="2026-05-31 23:59:59",
)
period.invalidate_model()
period_rows = period.search([])
for r in period_rows:
    opening = r.cost_initial + r.markup_initial + r.vat_initial
    moved_in = r.cost_in + r.markup_in + r.vat_in
    moved_out = r.cost_out + r.markup_out + r.vat_out
    corrections = r.cost_adjustment + r.markup_adjustment + r.vat_adjustment
    print(
        f"  {r.warehouse_id.code:4s} {r.product_id.name:24s} "
        f"{opening:9.2f} {moved_in:9.2f} {moved_out:9.2f} "
        f"{corrections:9.2f} {r.retail_value:9.2f}"
    )
print(
    f"  ----- {len(period_rows)} rows; opening + in + out + corrections = close -----"
)

print()
print("=" * 78)
print("PRODUCTS WHOSE SHELF PRICE NO LONGER MATCHES WHAT THE STOCK CARRIES")
print("=" * 78)
to_revalue = env["l10n.ro.stock.retail.report"].search([])
to_revalue = to_revalue.filtered(lambda r: round(r.price_gap_total, 2) != 0)
for r in to_revalue:
    print(
        f"  {r.warehouse_id.code:4s} {r.product_id.name:28s} "
        f"carried {r.retail_price_unit:8.2f} vs shelf "
        f"{r.current_price_unit:8.2f} -> {r.price_gap_total:10.2f} to settle"
    )
print(f"  ----- {len(to_revalue)} products awaiting a price change -----")


print()
print("=" * 78)
print("RETAIL PRICE CHANGE DOCUMENTS")
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
    f"  Purchase orders: {env['purchase.order'].search_count([])} "
    f"(total {pos_total:.2f} RON inc VAT)"
)
print(
    f"  Sale orders:     {env['sale.order'].search_count([])} "
    f"(total {sos_total:.2f} RON inc VAT)"
)
print(
    f"  Quants on hand:  {env['stock.quant'].search_count([('quantity', '>', 0)])} "
    "distinct rows"
)

env.cr.commit()
log("Demo committed.")
