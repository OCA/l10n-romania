# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon


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
