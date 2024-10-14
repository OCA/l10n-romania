# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields
from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account_landed_cost.tests.common import TestStockCommon


@tagged("post_install", "-at_install")
class TestStockPickingValued(TestStockCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super(TestStockPickingValued, cls).setUpClass(
            chart_template_ref=ro_template_ref
        )

        cls.env.company.anglo_saxon_accounting = True
        cls.env.company.l10n_ro_accounting = True
        cls.env.company.l10n_ro_stock_acc_price_diff = True
        company = cls.env.user.company_id
        # activare momenda RON si EUR
        cls.currency_eur = cls.env.ref("base.EUR")
        cls.currency_ron = cls.env.ref("base.RON")
        cls.currency_eur.active = True

        cls.currency_eur.rate_ids.create(
            {
                "name": "2021-01-01",
                "rate": 4.5,
                "company_id": cls.env.company.id,
                "currency_id": cls.currency_ron.id,
            }
        )

        # convertesc 1 EUR in RON
        cls.rate = cls.currency_eur._convert(
            1, cls.currency_ron, cls.env.company, fields.Date.today()
        )
        cls.partner = cls.env["res.partner"].create({"name": "Mr. Odoo"})
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_1.id,
                            "price_unit": 100,
                            "product_uom_qty": 1,
                        },
                    )
                ],
                "company_id": company.id,
            }
        )
        cls.sale_order2 = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_1.id,
                            "price_unit": 100,
                            "product_uom_qty": 1,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_1.id,
                            "price_unit": 100,
                            "product_uom_qty": 1,
                        },
                    ),
                ],
                "company_id": company.id,
            }
        )
        cls.sale_order.company_id.tax_calculation_rounding_method = "round_per_line"
        cls.purchase_order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_1.id,
                            "price_unit": 100,
                            "product_uom_qty": 1,
                        },
                    )
                ],
                "company_id": company.id,
            }
        )
        cls.purchase_order2 = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_1.id,
                            "price_unit": 100,
                            "product_uom_qty": 1,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_1.id,
                            "price_unit": 100,
                            "product_uom_qty": 1,
                        },
                    ),
                ],
                "company_id": company.id,
            }
        )
        # module_name = 'purchase_mrp'
        # module = cls.env['ir.module.module'].sudo().search([('name', '=', module_name)])
        # if module.state not in ('installed', 'to install', 'to upgrade'):
        #     module.button_immediate_install()

        cls.UoM = cls.env["uom.uom"]
        cls.categ_unit = cls.env.ref("uom.product_uom_categ_unit")

        cls.uom_unit = cls.env["uom.uom"].search(
            [("category_id", "=", cls.categ_unit.id), ("uom_type", "=", "reference")],
            limit=1,
        )
        cls.uom_unit.write({"name": "Test-Unit", "rounding": 0.01})

        # Creating all components

        cls.component_a = cls.env["product.product"].create(
            {
                "name": "Comp A",
                "uom_id": cls.uom_unit.id,
                "type": "product",
                "purchase_method": "receive",
                "categ_id": cls.category_fifo.id,
                "invoice_policy": "delivery",
                "list_price": 12,
                "standard_price": 12,
            }
        )

        cls.component_b = cls.env["product.product"].create(
            {
                "name": "Comp B",
                "uom_id": cls.uom_unit.id,
                "type": "product",
                "purchase_method": "receive",
                "categ_id": cls.category_fifo.id,
                "invoice_policy": "delivery",
                "list_price": 12,
                "standard_price": 12,
            }
        )

        # Create kit and bom

        cls.kit_1 = cls.env["product.product"].create(
            {
                "name": "Kit A",
                "uom_id": cls.uom_unit.id,
                "type": "product",
                "purchase_method": "receive",
                "categ_id": cls.category_fifo.id,
                "invoice_policy": "delivery",
                "list_price": 1,
                "standard_price": 1,
            }
        )
        cls.kit_2 = cls.env["product.product"].create(
            {
                "name": "Kit B",
                "uom_id": cls.uom_unit.id,
            }
        )

        cls.kit_3 = cls.env["product.product"].create(
            {
                "name": "Kit 2 Components",
                "uom_id": cls.uom_unit.id,
            }
        )

        cls.bom_kit_1 = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_1.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        cls.bom_kit_2 = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_1.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        cls.bom_kit_3 = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_3.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine = cls.env["mrp.bom.line"]
        BomLine.create(
            {
                "product_id": cls.component_a.id,
                "product_qty": 12.0,
                "bom_id": cls.bom_kit_1.id,
            }
        )

        BomLine.create(
            {
                "product_id": cls.component_b.id,
                "product_qty": 6.0,
                "bom_id": cls.bom_kit_2.id,
            }
        )

        BomLine.create(
            {
                "product_id": cls.component_b.id,
                "product_qty": 6.0,
                "bom_id": cls.bom_kit_3.id,
            }
        )
        BomLine.create(
            {
                "product_id": cls.component_b.id,
                "product_qty": 3.0,
                "bom_id": cls.bom_kit_3.id,
            }
        )

        cls.purchase_order3 = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.kit_1.id,
                            "price_unit": 24,
                            "product_qty": 1,
                        },
                    ),
                ],
                "company_id": company.id,
            }
        )

        cls.purchase_order4 = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.kit_1.id,
                            "price_unit": 24,
                            "product_qty": 1,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": cls.kit_2.id,
                            "price_unit": 36,
                            "product_qty": 1,
                        },
                    ),
                ],
                "company_id": company.id,
            }
        )

        cls.purchase_order5 = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.kit_3.id,
                            "price_unit": 42,
                            "product_qty": 2,
                        },
                    ),
                ],
                "company_id": company.id,
            }
        )

        cls.sale_order3 = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.kit_1.id,
                            "price_unit": 20,
                            "product_uom_qty": 1,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_1.id,
                            "price_unit": 100,
                            "product_uom_qty": 1,
                        },
                    ),
                ],
                "company_id": company.id,
            }
        )
