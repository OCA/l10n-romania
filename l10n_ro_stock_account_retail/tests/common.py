# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import Form

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon


class TestRetailCommon(TestROStockCommon):
    """Two fully configured retail shops and a plain depot.

    MAG1 and MAG2 each carry their own 371, 607, 378 and 4428, so an entry
    that lands on the wrong shop's accounts fails loudly instead of
    balancing by accident. Shelf prices are held VAT included throughout:
    the product is priced at 119 with 19% VAT, which is 100 net over a
    cost of 50 - a markup of 50 and a deferred VAT of 19 per unit.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        Account = cls.env["account.account"]
        cls.account_371 = company.account_stock_valuation_id
        cls.account_378 = Account.create(
            {
                "code": "378ret",
                "name": "Diferente de pret la marfuri (test)",
                "account_type": "asset_current",
                "company_ids": [(4, company.id)],
            }
        )
        cls.account_4428 = Account.create(
            {
                "code": "4428ret",
                "name": "TVA neexigibila (test)",
                "account_type": "liability_current",
                "company_ids": [(4, company.id)],
            }
        )
        company.l10n_ro_account_markup_id = cls.account_378
        company.l10n_ro_account_deferred_vat_id = cls.account_4428
        cls.tax_19 = cls.env["account.tax"].create(
            {
                "name": "TVA 19% retail",
                "amount_type": "percent",
                "amount": 19.0,
                "type_tax_use": "sale",
                "company_id": company.id,
            }
        )
        cls.retail_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Retail pricelist",
                "currency_id": company.currency_id.id,
                "company_id": company.id,
            }
        )
        cls.retail_warehouse = cls.env["stock.warehouse"].create(
            {
                "name": "Magazin",
                "code": "MAG",
                "l10n_ro_retail": True,
                "l10n_ro_retail_pricelist_id": cls.retail_pricelist.id,
            }
        )
        cls.retail_stock_loc = cls.retail_warehouse.lot_stock_id
        cls.product_retail = cls.env["product.product"].create(
            {
                "name": "Produs Magazin",
                "is_storable": True,
                "categ_id": cls.category_marfa_avg.id,
                "list_price": 119.0,
                "standard_price": 50.0,
                "taxes_id": [(6, 0, cls.tax_19.ids)],
            }
        )

        # --- Two fully-configured retail stores (mirrors a real multi-shop
        # setup: each store has its own 371/607 valuation accounts and its
        # own 378/4428 markup accounts), used to test transfers between
        # a non-retail depot and retail stores, and between two stores. ---
        cls.account_482 = Account.create(
            {
                "code": "482test",
                "name": "Decontari intre gestiuni (test)",
                "account_type": "asset_current",
                "company_ids": [(4, company.id)],
            }
        )
        company.l10n_ro_property_stock_transfer_account_id = cls.account_482

        cls.pricelist_mag1 = cls.env["product.pricelist"].create(
            {
                "name": "Retail pricelist MAG1",
                "currency_id": company.currency_id.id,
                "company_id": company.id,
            }
        )
        cls.warehouse_mag1 = cls.env["stock.warehouse"].create(
            {
                "name": "Magazin 1",
                "code": "MAG1",
                "l10n_ro_retail": True,
                "l10n_ro_retail_pricelist_id": cls.pricelist_mag1.id,
            }
        )
        cls.loc_mag1 = cls.warehouse_mag1.lot_stock_id
        cls.account_371_mag1 = cls.account_371.copy({"code": "371mag1"})
        cls.account_607_mag1 = cls.account_expense.copy({"code": "607mag1"})
        cls.account_378_mag1 = Account.create(
            {
                "code": "378mag1",
                "name": "Adaos comercial MAG1 (test)",
                "account_type": "asset_current",
                "company_ids": [(4, company.id)],
            }
        )
        cls.account_4428_mag1 = Account.create(
            {
                "code": "4428mag1",
                "name": "TVA neexigibila MAG1 (test)",
                "account_type": "liability_current",
                "company_ids": [(4, company.id)],
            }
        )
        cls.loc_mag1.write(
            {
                "l10n_ro_property_stock_valuation_account_id": (
                    cls.account_371_mag1.id
                ),
                "l10n_ro_property_account_expense_location_id": (
                    cls.account_607_mag1.id
                ),
                "l10n_ro_account_markup_id": cls.account_378_mag1.id,
                "l10n_ro_account_deferred_vat_id": cls.account_4428_mag1.id,
            }
        )

        cls.pricelist_mag2 = cls.env["product.pricelist"].create(
            {
                "name": "Retail pricelist MAG2",
                "currency_id": company.currency_id.id,
                "company_id": company.id,
            }
        )
        cls.warehouse_mag2 = cls.env["stock.warehouse"].create(
            {
                "name": "Magazin 2",
                "code": "MAG2",
                "l10n_ro_retail": True,
                "l10n_ro_retail_pricelist_id": cls.pricelist_mag2.id,
            }
        )
        cls.loc_mag2 = cls.warehouse_mag2.lot_stock_id
        cls.account_371_mag2 = cls.account_371.copy({"code": "371mag2"})
        cls.account_607_mag2 = cls.account_expense.copy({"code": "607mag2"})
        cls.account_378_mag2 = Account.create(
            {
                "code": "378mag2",
                "name": "Adaos comercial MAG2 (test)",
                "account_type": "asset_current",
                "company_ids": [(4, company.id)],
            }
        )
        cls.account_4428_mag2 = Account.create(
            {
                "code": "4428mag2",
                "name": "TVA neexigibila MAG2 (test)",
                "account_type": "liability_current",
                "company_ids": [(4, company.id)],
            }
        )
        cls.loc_mag2.write(
            {
                "l10n_ro_property_stock_valuation_account_id": (
                    cls.account_371_mag2.id
                ),
                "l10n_ro_property_account_expense_location_id": (
                    cls.account_607_mag2.id
                ),
                "l10n_ro_account_markup_id": cls.account_378_mag2.id,
                "l10n_ro_account_deferred_vat_id": cls.account_4428_mag2.id,
            }
        )

        # Every shop declares its shelf prices, because the module refuses to
        # guess one: a product with no rule on the retail pricelist cannot be
        # valued at its sale price, which is a price without VAT. These shops
        # price everything at the sale price read as a PVA - the products here
        # carry a VAT inclusive list price - and the tests that need a
        # different shelf price add a variant rule, which wins over this one.
        for pricelist in (
            cls.retail_pricelist,
            cls.pricelist_mag1,
            cls.pricelist_mag2,
        ):
            cls.env["product.pricelist.item"].with_context(
                skip_retail_price_change=True
            ).create(
                {
                    "pricelist_id": pricelist.id,
                    "applied_on": "3_global",
                    "compute_price": "formula",
                    "base": "list_price",
                    "price_discount": 0.0,
                }
            )

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------
    def _set_initial_stock(self, location, product, qty):
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": product.id,
                "location_id": location.id,
                "inventory_quantity": qty,
            }
        ).action_apply_inventory()

    def _do_transfer(self, src_location, dest_location, product, qty):
        picking_type = src_location.warehouse_id.int_type_id
        move = self.env["stock.move"].create(
            {
                "company_id": self.env.company.id,
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": qty,
                "location_id": src_location.id,
                "location_dest_id": dest_location.id,
                "picking_type_id": picking_type.id,
            }
        )
        move._action_confirm()
        move._action_assign()
        move._set_quantity_done(qty)
        move.picked = True
        move._action_done()
        return move

    def _lines_as_tuples(self, move):
        """(account_id, debit, credit) tuples for a posted account.move,
        rounded and sorted so the comparison is order-independent."""
        return sorted(
            (line.account_id.id, round(line.debit, 2), round(line.credit, 2))
            for line in move.line_ids
        )

    def _do_purchase_receipt(self, warehouse, product, qty, price_unit, qty_done=None):
        """Receive ``qty_done`` (default: everything ordered) against a PO for
        ``qty``. Receiving more than was ordered does not split the move, so
        the demand and the quantity actually valued part company."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.supplier_1.id,
                "picking_type_id": warehouse.in_type_id.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "price_unit": price_unit,
                        },
                    )
                ],
            }
        )
        po.button_confirm()
        picking = po.picking_ids
        picking.move_ids._set_quantity_done(qty if qty_done is None else qty_done)
        picking.move_ids.picked = True
        picking.button_validate()
        return po, picking.move_ids

    def _do_sale_delivery(self, warehouse, product, qty, price_unit, discount=0.0):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.customer_1.id,
                "warehouse_id": warehouse.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "price_unit": price_unit,
                            "discount": discount,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        picking = so.picking_ids
        picking.move_ids._set_quantity_done(qty)
        picking.move_ids.picked = True
        picking.button_validate()
        return picking.move_ids

    def _do_return(self, picking, qty):
        return_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=[picking.id],
                active_id=picking.id,
                active_model="stock.picking",
            )
        )
        return_wiz = return_form.save()
        return_wiz.product_return_moves.write({"quantity": qty, "to_refund": True})
        res = return_wiz.action_create_returns()
        return_picking = self.env["stock.picking"].browse(res["res_id"])
        return_picking.action_confirm()
        return_picking.action_assign()
        return_picking.move_ids._set_quantity_done(qty)
        return_picking.move_ids.picked = True
        return_picking._action_done()
        return return_picking.move_ids
